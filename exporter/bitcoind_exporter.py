#!/usr/bin/env python3
"""Prometheus exporter for the bitcoind fields that node alerting needs.

Standard library only. Each scrape calls bitcoind's JSON-RPC (a single batch request)
and returns the result, so there is no background polling and no stale cache.

Configuration (environment variables):
  BITCOIND_RPC_URL       default http://127.0.0.1:8332/
  BITCOIND_RPC_COOKIE    path to bitcoind's .cookie file (preferred), or
  BITCOIND_RPC_USER / BITCOIND_RPC_PASSWORD
  BITCOIND_RPC_TIMEOUT   seconds, default 5 (keep it below the Prometheus scrape timeout)
  EXPORTER_LISTEN        host:port, default 127.0.0.1:9332

The exporter only needs read-only calls. Give it its own RPC user, limited with
  -rpcauth=<exporter>:<hash> -rpcwhitelist=<exporter>:getblockchaininfo,getnetworkinfo,getmempoolinfo,getrpcinfo,uptime,getchaintips
"""

import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RPC_URL = os.environ.get("BITCOIND_RPC_URL", "http://127.0.0.1:8332/")
RPC_COOKIE = os.environ.get("BITCOIND_RPC_COOKIE")
RPC_USER = os.environ.get("BITCOIND_RPC_USER")
RPC_PASSWORD = os.environ.get("BITCOIND_RPC_PASSWORD")
RPC_TIMEOUT = float(os.environ.get("BITCOIND_RPC_TIMEOUT", "5"))
LISTEN = os.environ.get("EXPORTER_LISTEN", "127.0.0.1:9332")

# Methods fetched on every scrape, in one JSON-RPC batch.
METHODS = [
    "getblockchaininfo",
    "getnetworkinfo",
    "getmempoolinfo",
    "getrpcinfo",
    "uptime",
    "getchaintips",
]

RPC_ERRORS = {m: 0 for m in METHODS + ["batch"]}

# JSON-RPC error code bitcoind returns while it loads the block index, verifies
# blocks or replays after an unclean shutdown (RPC_IN_WARMUP).
RPC_IN_WARMUP = -28

# Best block hash -> Unix time this exporter first saw it as the tip. Block header
# timestamps can be up to two hours in the future (testnet4 miners routinely set
# them ahead), so the age of the tip is measured from when the node had it.
TIP_SEEN = {"hash": None, "time": 0.0}
TIP_LOCK = threading.Lock()  # scrapes run on concurrent threads


class RPCError(Exception):
    pass


def _auth_header():
    if RPC_COOKIE:
        # Re-read on every scrape: bitcoind writes a new cookie on each restart.
        with open(RPC_COOKIE) as f:
            creds = f.read().strip()
    elif RPC_USER is not None:
        creds = "%s:%s" % (RPC_USER, RPC_PASSWORD or "")
    else:
        raise RuntimeError("set BITCOIND_RPC_COOKIE or BITCOIND_RPC_USER/BITCOIND_RPC_PASSWORD")
    return "Basic " + base64.b64encode(creds.encode()).decode()


def rpc_batch(methods):
    body = json.dumps(
        [{"jsonrpc": "1.0", "id": i, "method": m, "params": []} for i, m in enumerate(methods)]
    ).encode()
    req = urllib.request.Request(
        RPC_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": _auth_header()},
    )
    with urllib.request.urlopen(req, timeout=RPC_TIMEOUT) as resp:
        replies = json.load(resp)
    if not isinstance(replies, list):
        raise RPCError("unexpected reply to a batch request: %r" % (replies,))
    out, errors = {}, {}
    for r in replies:
        rid = r.get("id") if isinstance(r, dict) else None
        if not isinstance(rid, int) or not 0 <= rid < len(methods):
            raise RPCError("unexpected reply in batch: %r" % (r,))
        method = methods[rid]
        if r.get("error"):
            RPC_ERRORS[method] += 1
            errors[method] = r["error"]
        else:
            out[method] = r.get("result")
    return out, errors


def tip_seen_time(best_hash, header_time, now):
    """When this exporter first saw best_hash as the tip.

    On the first scrape after the exporter starts it cannot know, so it takes the
    earlier of now and the header time.
    """
    with TIP_LOCK:
        if best_hash != TIP_SEEN["hash"]:
            first = TIP_SEEN["hash"] is None
            TIP_SEEN["hash"] = best_hash
            TIP_SEEN["time"] = min(now, header_time) if first and header_time else now
        return TIP_SEEN["time"]


def _esc(v):
    return str(v).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class Metrics:
    def __init__(self):
        self.lines = []
        self.seen = set()

    def add(self, name, mtype, help_text, value, labels=None):
        if name not in self.seen:
            self.seen.add(name)
            self.lines.append("# HELP %s %s" % (name, help_text))
            self.lines.append("# TYPE %s %s" % (name, mtype))
        lbl = ""
        if labels:
            lbl = "{" + ",".join('%s="%s"' % (k, _esc(v)) for k, v in sorted(labels.items())) + "}"
        self.lines.append("%s%s %s" % (name, lbl, repr(float(value))))

    def render(self):
        return ("\n".join(self.lines) + "\n").encode()


def collect():
    m = Metrics()
    start = time.monotonic()
    errors = {}
    try:
        r, errors = rpc_batch(METHODS)
    except (urllib.error.URLError, OSError, ValueError, RuntimeError, RPCError) as e:
        RPC_ERRORS["batch"] += 1
        print("bitcoind RPC failed: %s" % e, file=sys.stderr)
        r = {}

    # During warmup bitcoind answers the batch with HTTP 200 and error -28 for every
    # call, so a successful HTTP request alone does not mean the node is usable.
    bci = r.get("getblockchaininfo")
    if not isinstance(bci, dict):
        bci = None
    warmup = any(isinstance(e, dict) and e.get("code") == RPC_IN_WARMUP for e in errors.values())
    m.add("bitcoind_up", "gauge", "1 if bitcoind answered getblockchaininfo on the last scrape", 1 if bci else 0)
    m.add("bitcoind_rpc_warmup", "gauge", "1 if bitcoind answered RPC with 'in warmup' (-28) on the last scrape",
          1 if warmup else 0)

    if bci:
        m.add("bitcoind_blocks", "gauge", "Height of the most-work fully validated chain", bci["blocks"])
        m.add("bitcoind_headers", "gauge", "Height of the most-work header chain", bci["headers"])
        m.add("bitcoind_initial_block_download", "gauge", "1 while bitcoind is in initial block download",
              1 if bci.get("initialblockdownload") else 0)
        m.add("bitcoind_verification_progress", "gauge", "Estimated chain verification progress (0..1)",
              bci.get("verificationprogress", 0))
        if "time" in bci:
            m.add("bitcoind_best_block_timestamp_seconds", "gauge", "Header timestamp of the best block", bci["time"])
        if bci.get("bestblockhash"):
            m.add("bitcoind_best_block_seen_timestamp_seconds", "gauge",
                  "Unix time the exporter first saw the current best block", tip_seen_time(
                      bci["bestblockhash"], bci.get("time", 0), time.time()))
        if "mediantime" in bci:
            m.add("bitcoind_best_block_median_time_seconds", "gauge", "Median time past of the best block",
                  bci["mediantime"])
        m.add("bitcoind_size_on_disk_bytes", "gauge", "Estimated size of the block and undo files",
              bci.get("size_on_disk", 0))
        m.add("bitcoind_pruned", "gauge", "1 if the node prunes block files", 1 if bci.get("pruned") else 0)
        warnings = bci.get("warnings") or []
        if isinstance(warnings, str):
            warnings = [warnings] if warnings else []
        m.add("bitcoind_warnings", "gauge", "Number of node warnings reported by getblockchaininfo", len(warnings))

    net = r.get("getnetworkinfo")
    if not isinstance(net, dict):
        net = None
    if net:
        if "connections_in" in net:
            m.add("bitcoind_peers", "gauge", "Connected peers by direction", net["connections_in"], {"direction": "in"})
            m.add("bitcoind_peers", "gauge", "Connected peers by direction", net["connections_out"],
                  {"direction": "out"})
        m.add("bitcoind_network_active", "gauge", "1 if P2P networking is enabled", 1 if net.get("networkactive") else 0)

    if bci or net:
        m.add("bitcoind_info", "gauge", "Node information (always 1)", 1, {
            "chain": (bci or {}).get("chain", ""),
            "version": (net or {}).get("version", ""),
            "subversion": (net or {}).get("subversion", ""),
        })

    mp = r.get("getmempoolinfo")
    if isinstance(mp, dict):
        m.add("bitcoind_mempool_transactions", "gauge", "Transactions in the mempool", mp.get("size", 0))
        m.add("bitcoind_mempool_usage_bytes", "gauge", "Memory used by the mempool", mp.get("usage", 0))
        m.add("bitcoind_mempool_max_bytes", "gauge", "Configured mempool memory limit", mp.get("maxmempool", 0))
        m.add("bitcoind_mempool_min_fee_btc_per_kvb", "gauge", "Minimum fee rate for mempool acceptance",
              mp.get("mempoolminfee", 0))
        m.add("bitcoind_mempool_loaded", "gauge", "1 once the mempool has been loaded from disk",
              1 if mp.get("loaded") else 0)

    rpcinfo = r.get("getrpcinfo")
    if isinstance(rpcinfo, dict):
        # Includes the getrpcinfo call itself.
        m.add("bitcoind_rpc_active_commands", "gauge", "RPC commands executing at scrape time",
              len(rpcinfo.get("active_commands", [])))

    if isinstance(r.get("uptime"), (int, float)):
        m.add("bitcoind_uptime_seconds", "gauge", "Seconds since bitcoind started", r["uptime"])

    tips = r.get("getchaintips")
    if isinstance(tips, list):
        counts = {}
        for t in tips:
            counts[t.get("status", "unknown")] = counts.get(t.get("status", "unknown"), 0) + 1
        for status in ("active", "valid-fork", "valid-headers", "headers-only", "invalid"):
            m.add("bitcoind_chain_tips", "gauge", "Known chain tips by status", counts.pop(status, 0),
                  {"status": status})
        for status, n in counts.items():
            m.add("bitcoind_chain_tips", "gauge", "Known chain tips by status", n, {"status": status})

    for method, n in RPC_ERRORS.items():
        m.add("bitcoind_exporter_rpc_errors_total", "counter",
              "RPC failures seen by the exporter (method=batch means the whole request failed)", n,
              {"method": method})
    m.add("bitcoind_exporter_scrape_duration_seconds", "gauge", "Time spent querying bitcoind for this scrape",
          time.monotonic() - start)
    return m.render()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        try:
            body = collect()
        except Exception as e:  # never reset the scrape connection; report bitcoind as down
            print("collect failed: %r" % (e,), file=sys.stderr)
            body = Metrics()
            body.add("bitcoind_up", "gauge", "1 if bitcoind answered getblockchaininfo on the last scrape", 0)
            body = body.render()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    host, _, port = LISTEN.rpartition(":")
    server = ThreadingHTTPServer((host.strip("[]") or "0.0.0.0", int(port)), Handler)
    print("bitcoind exporter listening on %s, bitcoind at %s" % (LISTEN, RPC_URL), file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
