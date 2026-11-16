#!/usr/bin/env python3
"""Run one game-day drill on the lab and record it for the replay page.

  python3 gameday/gameday.py SCENARIO --out docs/replay/SCENARIO.json

Each drill injects a fault into a real bitcoind + electrs, then waits like an on-call
engineer: when the page (or ticket) arrives it waits RESPONSE_DELAY seconds for the ack and
runbook, applies the runbook's mitigation, and waits until every alert has resolved.

While it runs it records, every few seconds: key metrics and the alert states from
Prometheus, active and inhibited alerts from Alertmanager, and every notification
Alertmanager sends to the page and ticket webhooks (this script is the webhook).

LAB below describes the testnet4 lab this ran on: user systemd units started with
systemd-run, Prometheus on 19090, Alertmanager on 19093 with examples/alertmanager.yml.
Change it for your own lab. Standard library only.
"""

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.path.expanduser("~")
LAB = {
    "prometheus": "http://127.0.0.1:19090",
    "alertmanager": "http://127.0.0.1:19093",
    "webhook": ("127.0.0.1", 19095),
    "prometheus_config": HOME + "/bnm/live/prometheus.yml",
    "bitcoind_unit": "t4-bitcoind",
    "bitcoind": [HOME + "/electrs-mem/core/bitcoin-32.1/bin/bitcoind", "-testnet4",
                 "-datadir=" + HOME + "/electrs-mem/btcd", "-server=1", "-rpcbind=127.0.0.1",
                 "-rpcallowip=127.0.0.1", "-rpcuser=electrs", "-rpcpassword=electrs-local",
                 "-dbcache=300", "-listen=0", "-daemon=0"],
    "cli": [HOME + "/electrs-mem/core/bitcoin-32.1/bin/bitcoin-cli", "-testnet4", "-rpcport=48332",
            "-rpcuser=electrs", "-rpcpassword=electrs-local"],
    "rpc_url": "http://127.0.0.1:48332/",
    "rpc_auth": ("electrs", "electrs-local"),
    "electrs_unit": "bnm-electrs",
    "electrs": ["/bin/bash", "-c", 'exec "$0" "$@" >> ' + HOME + "/bnm/logs/electrs.log 2>&1",
                HOME + "/electrs-mem/target-rocky/release/electrs", "-v", "--network", "testnet4",
                "--daemon-dir", HOME + "/electrs-mem/btcd",
                "--blocks-dir", HOME + "/electrs-mem/btcd/testnet4/blocks",
                "--cookie", "electrs:electrs-local", "--daemon-rpc-addr", "127.0.0.1:48332",
                "--db-dir", HOME + "/electrs-mem/db/r2-fix", "--http-addr", "127.0.0.1:43002",
                "--electrum-rpc-addr", "127.0.0.1:43001", "--monitoring-addr", "127.0.0.1:44224"],
    "electrs_rest": "http://127.0.0.1:43002",
    "electrs_log": HOME + "/bnm/logs/electrs.log",
}
SAMPLE_EVERY = 5          # seconds between recorder samples
# Side effects of the drills themselves (they restart things on purpose): recorded, but they are not
# the page the on-call is waiting for.
NOT_A_TRIGGER = {"BitcoindRestartLoop", "ElectrsRestartLoop"}
RESPONSE_DELAY = 120      # ack + read the runbook, after the first notification

METRICS = {
    "bitcoind_up": 'max(bitcoind_up{job="bitcoind"})',
    "warmup": 'max(bitcoind_rpc_warmup{job="bitcoind"})',
    "exporter_scraped": 'max(up{job="bitcoind"})',
    "electrs_scraped": 'max(up{job="electrs"})',
    "blocks": 'max(bitcoind_blocks{job="bitcoind"})',
    "headers": 'max(bitcoind_headers{job="bitcoind"})',
    "invalid_tip": 'max(bitcoind_invalid_tip_height{job="bitcoind"})',
    "electrs_tip": 'max(node:electrs_tip_height:max)',
    "peers": 'sum(bitcoind_peers{job="bitcoind"})',
    "electrs_rss": 'max(process_memory_rss{job="electrs"})',
    "rest_errors_5m": 'max(node:electrs_slo_errors:ratio_rate5m{slo="rest-availability"})',
    "rpc_busy_15m": 'sum(increase(daemon_rpc_proxied{job="electrs",result=~"busy|unavailable"}[15m]))',
    "rpc_active": 'max(bitcoind_rpc_active_commands{job="bitcoind"})',
}


# ------------------------------------------------------------------ helpers
def http_json(url, data=None, auth=None, timeout=10):
    req = urllib.request.Request(url, data=data)
    if auth:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(("%s:%s" % auth).encode()).decode())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def promql(q):
    try:
        res = http_json(LAB["prometheus"] + "/api/v1/query?" + urllib.parse.urlencode({"query": q}))
        return res["data"]["result"]
    except Exception:
        return None


def sh(cmd, check=False):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError("%s: %s" % (cmd, p.stderr.strip()))
    return p.stdout.strip()


def cli(*args):
    return sh(LAB["cli"] + list(args))


def run_unit(unit, argv, props=()):
    sh(["systemctl", "--user", "reset-failed", unit])
    cmd = ["systemd-run", "--user", "--unit", unit, "--slice", "app.slice", "--collect"]
    for p in props:
        cmd += ["-p", p]
    sh(cmd + argv, check=True)


def unit_stopped(unit):
    return sh(["systemctl", "--user", "is-active", unit]) not in ("active", "activating", "deactivating", "reloading")


def rpc_ready():
    """bitcoind answers a real call (the recorded metrics can still hold the last scrape)."""
    return cli("getblockcount").isdigit()


def stop_unit(unit, signal=None):
    if signal:
        sh(["systemctl", "--user", "kill", "-s", signal, unit])
    else:
        sh(["systemctl", "--user", "stop", unit])


# ------------------------------------------------------------------ recorder
class Recorder:
    def __init__(self, scenario, out=None):
        self.out = out
        self.t0 = time.time()
        self.data = {"scenario": scenario, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "sample_every": SAMPLE_EVERY, "response_delay": RESPONSE_DELAY,
                     "samples": [], "alerts": [], "notifications": [], "events": []}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.notified = threading.Event()
        self.last_alert_state = None
        self.inject_t = None

    def now(self):
        return round(time.time() - self.t0, 1)

    def event(self, kind, text):
        if kind == "inject" and self.inject_t is None:
            self.inject_t = self.now()
        with self.lock:
            self.data["events"].append({"t": self.now(), "kind": kind, "text": text})
        print("[%6.0fs] %-8s %s" % (self.now(), kind, text), flush=True)

    def notification(self, receiver, body):
        alerts = sorted({(a["labels"].get("alertname"), a["status"]) for a in body.get("alerts", [])})
        with self.lock:
            self.data["notifications"].append({"t": self.now(), "receiver": receiver,
                                               "status": body.get("status"),
                                               "alerts": [{"alertname": n, "status": s} for n, s in alerts]})
        self.notified.set()
        print("[%6.0fs] notify   %s %s %s" % (self.now(), receiver, body.get("status"),
                                              ", ".join(n for n, _ in alerts)), flush=True)

    def sample(self):
        m = {}
        for key, q in METRICS.items():
            r = promql(q)
            m[key] = round(float(r[0]["value"][1]), 6) if r else None
        state = {"firing": [], "pending": [], "inhibited": []}
        for a in promql("ALERTS") or []:
            state[a["metric"]["alertstate"]].append(a["metric"]["alertname"])
        try:
            for a in http_json(LAB["alertmanager"] + "/api/v2/alerts"):
                if a["status"]["state"] == "suppressed" and a["status"].get("inhibitedBy"):
                    state["inhibited"].append(a["labels"]["alertname"])
        except Exception:
            pass
        state = {k: sorted(set(v)) for k, v in state.items()}
        with self.lock:
            self.data["samples"].append({"t": self.now(), "m": m})
            if state != self.last_alert_state:
                self.data["alerts"].append(dict(t=self.now(), **state))
                self.last_alert_state = state
        return state

    def save(self):
        """Write the recording so far; called after every sample, so a stopped run keeps its data."""
        if not self.out:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.out)), exist_ok=True)
        with self.lock:
            text = json.dumps(self.data, separators=(",", ":"))
        with open(self.out + ".tmp", "w") as f:
            f.write(text)
        os.replace(self.out + ".tmp", self.out)

    def loop(self):
        while not self.stop.is_set():
            self.sample()
            self.save()
            self.stop.wait(SAMPLE_EVERY)

    def serve_webhook(self):
        rec = self

        class Hook(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                rec.notification(self.path.strip("/"), body)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(LAB["webhook"], Hook)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    # ---- waits used by the scenarios
    def wait_notification(self, timeout):
        """Wait for the first firing notification, then the responder's ack + runbook delay."""
        self.notified.clear()
        end = time.time() + timeout
        def trigger(n):
            # Only what the fault caused: after the injection, and not a drill side effect.
            return (n["status"] == "firing" and n["t"] >= (self.inject_t or 0)
                    and any(a["alertname"] not in NOT_A_TRIGGER for a in n["alerts"]))
        while time.time() < end:
            first = next((n for n in self.data["notifications"] if trigger(n)), None)
            if first:
                self.event("ack", "%s received %s; on-call acks and opens the runbook" % (
                    first["receiver"], ", ".join(a["alertname"] for a in first["alerts"])))
                time.sleep(RESPONSE_DELAY)
                return True
            self.notified.wait(5)
            self.notified.clear()
        self.event("note", "no page or ticket within %d minutes" % (timeout // 60))
        return False

    def wait_until(self, what, fn, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if fn():
                    self.event("observe", what)
                    return True
            except Exception:
                pass
            time.sleep(SAMPLE_EVERY)
        self.event("note", "timed out waiting for: " + what)
        return False

    def wait_all_clear(self, timeout=1500):
        def clear():
            s = self.last_alert_state or {}
            if set(s.get("firing", []) + s.get("pending", [])) - NOT_A_TRIGGER:
                return False
            fired = {a["alertname"] for n in self.data["notifications"] if n["status"] == "firing"
                     and n["t"] >= (self.inject_t or 0) for a in n["alerts"]} - NOT_A_TRIGGER
            resolved = {a["alertname"] for n in self.data["notifications"] for a in n["alerts"]
                        if a["status"] == "resolved"}
            return fired <= resolved
        return self.wait_until("all alerts resolved and resolved notifications delivered", clear, timeout)


# ------------------------------------------------------------------ scenarios
def m(rec, key):
    return rec.data["samples"][-1]["m"].get(key) if rec.data["samples"] else None


def bitcoind_crash(rec):
    rec.event("inject", "kill -9 bitcoind (a remote crash such as CVE-2018-17144)")
    stop_unit(LAB["bitcoind_unit"], "KILL")
    rec.wait_notification(15 * 60)
    rec.event("action", "runbook bitcoind-down: start bitcoind again")
    run_unit(LAB["bitcoind_unit"], LAB["bitcoind"])
    rec.wait_until("bitcoind answering RPC again", rpc_ready, 30 * 60)
    rec.wait_until("electrs caught up with bitcoind",
                   lambda: m(rec, "electrs_tip") is not None and m(rec, "electrs_tip") >= m(rec, "blocks"), 15 * 60)


def electrs_oom(rec):
    rec.event("inject", "restart electrs under a 300 MiB memory limit, no swap (the OOM kills in electrs#215)")
    stop_unit(LAB["electrs_unit"])
    time.sleep(3)
    run_unit(LAB["electrs_unit"], LAB["electrs"],
             ["MemoryMax=300M", "MemorySwapMax=0", "Restart=always", "RestartSec=15"])
    rec.wait_notification(25 * 60)
    kills = sh("journalctl -k --since '-30min' --no-pager | grep -c 'Killed process .*(electrs)'")
    rec.event("observe", "kernel log: electrs OOM-killed %s times" % (kills or "?"))
    rec.event("action", "runbook electrs-memory-high: remove the limit (give electrs the memory it needs) and restart")
    stop_unit(LAB["electrs_unit"])
    time.sleep(3)
    run_unit(LAB["electrs_unit"], LAB["electrs"])
    rec.wait_until("electrs serving again", lambda: m(rec, "electrs_scraped") == 1, 10 * 60)


def network_isolation(rec):
    rec.event("inject", "bitcoin-cli setnetworkactive false (node cut off from every peer)")
    cli("setnetworkactive", "false")
    rec.wait_notification(25 * 60)
    rec.event("action", "runbook bitcoind-no-peers: restore networking (setnetworkactive true)")
    cli("setnetworkactive", "true")
    rec.wait_until("peers back", lambda: (m(rec, "peers") or 0) >= 4, 15 * 60)


def consensus_split(rec):
    start = int(cli("getblockcount"))
    invalidated = []
    # Reject the tip. testnet4 often has a competing block at the same height; reject those too
    # until the node sits below the chain the network is building on.
    for _ in range(4):
        h = cli("getbestblockhash")
        cli("invalidateblock", h)
        invalidated.append(h)
        if int(cli("getblockcount")) < start:
            break
    rec.event("inject", "invalidateblock on the tip (%d block(s)): the node now rejects the chain the "
                        "network follows, as 0.7 nodes did in March 2013 (BIP 50)" % len(invalidated))
    rec.event("observe", "node at height %s, network chain at %d" % (cli("getblockcount"), start))
    rec.wait_notification(25 * 60)
    rec.event("action", "runbook bitcoind-rejected-chain-ahead: cause found (a manual invalidateblock); "
                        "reconsiderblock")
    for h in invalidated:
        cli("reconsiderblock", h)
    rec.wait_until("node back on the network's chain", lambda: int(cli("getblockcount")) >= start, 10 * 60)


def rpc_overload(rec):
    rec.event("inject", "restart bitcoind with -rpcworkqueue=2 -rpcthreads=1, then flood it with "
                        "getblock calls (a backend fetching too much at once, mempool#4178)")
    stop_unit(LAB["bitcoind_unit"])
    rec.wait_until("bitcoind stopped", lambda: unit_stopped(LAB["bitcoind_unit"]), 300)
    run_unit(LAB["bitcoind_unit"], LAB["bitcoind"] + ["-rpcworkqueue=2", "-rpcthreads=1"])
    rec.wait_until("bitcoind answering RPC again", rpc_ready, 15 * 60)
    tip = int(cli("getblockcount"))
    stop = threading.Event()
    counts = [0, 0]  # answered, rejected or failed

    def flood():
        i = 0
        while not stop.is_set():
            i += 1
            try:
                body = json.dumps({"method": "getblockhash", "params": [tip - (i % 2000)], "id": i}).encode()
                bh = http_json(LAB["rpc_url"], body, LAB["rpc_auth"])["result"]
                body = json.dumps({"method": "getblock", "params": [bh, 2], "id": i}).encode()
                http_json(LAB["rpc_url"], body, LAB["rpc_auth"], timeout=30)
                counts[0] += 1
            except Exception:
                counts[1] += 1

    def broadcast():
        # Wallets keep broadcasting during congestion; electrs proxies these to bitcoind.
        while not stop.is_set():
            try:
                urllib.request.urlopen(urllib.request.Request(LAB["electrs_rest"] + "/tx", data=b"00"), timeout=10)
            except Exception:
                pass
            time.sleep(0.5)

    threads = [threading.Thread(target=flood, daemon=True) for _ in range(16)]
    threads.append(threading.Thread(target=broadcast, daemon=True))
    for t in threads:
        t.start()
    rec.event("observe", "16 RPC clients and a broadcast loop running")

    def watch_electrs():
        while not stop.is_set():
            if unit_stopped(LAB["electrs_unit"]):
                last = sh("grep 'server failed' %s | tail -1" % shlex.quote(LAB["electrs_log"]))
                rec.event("observe", "electrs exited: " + (last.split("ERROR ", 1)[-1][:160] or "no log line"))
                return
            time.sleep(2)
    threading.Thread(target=watch_electrs, daemon=True).start()
    try:
        rec.wait_notification(25 * 60)
        rec.event("observe", "flood so far: %d getblock calls answered, %d rejected or failed" % tuple(counts))
        rec.event("action", "runbook electrs-bitcoind-rpc-errors: stop the heavy client and restart bitcoind "
                            "with the default work queue")
    finally:
        # Also on an interrupted run: never leave bitcoind with the tiny work queue.
        stop.set()
        stop_unit(LAB["bitcoind_unit"])
        rec.wait_until("bitcoind stopped", lambda: unit_stopped(LAB["bitcoind_unit"]), 300)
        run_unit(LAB["bitcoind_unit"], LAB["bitcoind"])
    rec.wait_until("bitcoind answering RPC again", rpc_ready, 15 * 60)
    if unit_stopped(LAB["electrs_unit"]):
        rec.event("action", "runbook electrs-down: electrs exited on bitcoind's 503; start it again")
        run_unit(LAB["electrs_unit"], LAB["electrs"])
        rec.wait_until("electrs serving again", lambda: m(rec, "electrs_scraped") == 1, 10 * 60)


def monitoring_gap(rec):
    cfg = LAB["prometheus_config"]
    original = open(cfg).read()
    start = original.index("  - job_name: bitcoind")
    end = original.index("  - job_name: electrs")
    rec.event("inject", "deploy a Prometheus config that no longer scrapes bitcoind (a selector or "
                        "relabel mistake: the exporter vanishes, not fails)")
    open(cfg, "w").write(original[:start] + original[end:])
    urllib.request.urlopen(urllib.request.Request(LAB["prometheus"] + "/-/reload", data=b""))
    try:
        rec.wait_notification(15 * 60)
        rec.event("action", "runbook bitcoind-down (target missing): roll back the config")
    finally:
        open(cfg, "w").write(original)
        urllib.request.urlopen(urllib.request.Request(LAB["prometheus"] + "/-/reload", data=b""))
    rec.wait_until("bitcoind scraped again", lambda: m(rec, "exporter_scraped") == 1, 5 * 60)


SCENARIOS = {
    "bitcoind-crash": bitcoind_crash,
    "electrs-oom": electrs_oom,
    "network-isolation": network_isolation,
    "consensus-split": consensus_split,
    "rpc-overload": rpc_overload,
    "monitoring-gap": monitoring_gap,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--baseline", type=int, default=60, help="seconds to record before the fault")
    args = ap.parse_args()

    # Stopping the run (systemctl stop sends SIGTERM) still runs each drill's clean-up.
    signal.signal(signal.SIGTERM, lambda *a: sys.exit("stopped"))
    rec = Recorder(args.scenario, args.out)
    srv = rec.serve_webhook()
    state = rec.sample()
    active = set(state["firing"] + state["pending"]) - NOT_A_TRIGGER
    if active:
        sys.exit("alerts already active, not starting: %s" % sorted(active))
    threading.Thread(target=rec.loop, daemon=True).start()
    rec.event("note", "baseline: no alerts pending or firing" if not (state["firing"] or state["pending"])
              else "baseline: only %s active (from earlier drills restarting bitcoind)" % ", ".join(state["firing"] + state["pending"]))
    time.sleep(args.baseline)
    try:
        SCENARIOS[args.scenario](rec)
        rec.wait_all_clear()
        rec.event("resolved", "all clear")
        time.sleep(30)
    finally:
        rec.stop.set()
        rec.save()
        print("wrote", args.out, flush=True)
        srv.shutdown()


if __name__ == "__main__":
    main()
