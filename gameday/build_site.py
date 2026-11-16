#!/usr/bin/env python3
"""Bundle the game-day recordings and the real incidents they are based on into docs/replay/data.js.

  python3 gameday/build_site.py docs/replay/*.json

docs/index.html (the GitHub Pages replay) reads window.GAMEDAY from that file, so the page
works from github.io and from a local checkout alike.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Order on the page, what was simulated, and the public incident each drill is based on.
SCENARIOS = [
    {
        "id": "bitcoind-crash",
        "title": "bitcoind crashes",
        "fault": "kill -9 on bitcoind, then a restart through its warmup",
        "charts": [{"key": "bitcoind_up", "label": "bitcoind answering RPC", "kind": "state"},
                   {"key": "warmup", "label": "bitcoind warming up (RPC -28)", "kind": "state"},
                   {"key": "rest_errors_5m", "label": "electrs REST error ratio, 5m", "unit": "pct"}],
        "incidents": [
            {"name": "CVE-2018-17144", "date": "September 2018",
             "summary": "A block that spent the same output twice in one transaction crashed Bitcoin Core 0.14 to "
                        "0.16.2 with an assertion failure, and 0.15 to 0.16.2 could also be made to inflate the "
                        "supply. Anyone able to mine one such block could take nodes down; operators had to "
                        "upgrade to 0.16.3.",
             "url": "https://bitcoincore.org/en/2018/09/20/notice/"},
            {"name": "bitcoin/bitcoin#11600", "date": "2017 to 2025",
             "summary": "After an unclean shutdown, Bitcoin Core replayed blocks at startup for hours on nodes "
                        "with a large dbcache, and could not be stopped while it did. The drill's restart checks "
                        "that a warmup like this pages only if it runs long.",
             "url": "https://github.com/bitcoin/bitcoin/issues/11600"},
        ],
    },
    {
        "id": "consensus-split",
        "title": "Node rejects the network's chain",
        "fault": "invalidateblock on the tip, so the node refuses the chain its peers build on",
        "charts": [{"key": "blocks", "label": "bitcoind height", "kind": "value"},
                   {"key": "invalid_tip", "label": "highest block this node marked invalid", "kind": "value"}],
        "incidents": [
            {"name": "BIP 50: the March 2013 chain fork", "date": "March 2013",
             "summary": "A block with more inputs than any before it was valid for Bitcoin 0.8 nodes but rejected "
                        "by 0.7 nodes, whose database lock limit was too low. The network split in two; pools "
                        "downgraded to end it, and at least one double spend happened during the split.",
             "url": "https://github.com/bitcoin/bips/blob/master/bip-0050.mediawiki"},
            {"name": "bitcoin/bitcoin#26112", "date": "September 2022",
             "summary": "A node that ran out of disk space marked a valid block invalid and stayed stuck below the "
                        "network's tip after a restart, until the operator freed space and ran reconsiderblock.",
             "url": "https://github.com/bitcoin/bitcoin/issues/26112"},
            {"name": "BIP 66 fork alert", "date": "July 2015",
             "summary": "Miners that did not validate blocks built on an invalid block after the BIP 66 soft fork. "
                        "Up-to-date nodes saw a longer invalid chain and rejected it.",
             "url": "https://bitcoin.org/en/alert/2015-07-04-spv-mining"},
        ],
    },
    {
        "id": "network-isolation",
        "title": "Node cut off from its peers",
        "fault": "bitcoin-cli setnetworkactive false",
        "charts": [{"key": "peers", "label": "bitcoind peers", "kind": "value"},
                   {"key": "blocks", "label": "bitcoind height", "kind": "value"}],
        "incidents": [
            {"name": "bitcoin/bitcoin#48", "date": "January 2011",
             "summary": "After the host's IP address changed, the node's connection count drifted to 0 and stayed "
                        "there. It stopped receiving blocks without any error and did not reconnect on its own.",
             "url": "https://github.com/bitcoin/bitcoin/issues/48"},
            {"name": "CVE-2024-52912 (vulnerability, not exploited)", "date": "disclosed July 2024",
             "summary": "Peers could skew a node's clock so it rejected new blocks and split from the network. "
                        "Fixed in Bitcoin Core 0.21.0.",
             "url": "https://bitcoincore.org/en/2024/07/03/disclose-timestamp-overflow/"},
        ],
    },
    {
        "id": "electrs-oom",
        "title": "electrs killed for memory",
        "fault": "electrs restarted under a 300 MiB memory limit with no swap",
        "charts": [{"key": "electrs_rss", "label": "electrs resident memory", "unit": "bytes"},
                   {"key": "electrs_scraped", "label": "electrs metrics reachable", "kind": "state"}],
        "incidents": [
            {"name": "Blockstream/electrs#215", "date": "May 2026",
             "summary": "On a 16 GB host, electrs's full RocksDB compaction peaked near 15 GB and the kernel killed "
                        "it ('Failed with result oom-kill'). Capping memory in systemd stopped the kills, but then "
                        "compaction never finished. The memory needed is not documented.",
             "url": "https://github.com/Blockstream/electrs/issues/215"},
            {"name": "romanz/electrs#453", "date": "August 2021",
             "summary": "On an 8 GB Raspberry Pi, electrs finished indexing, logged 'starting full compaction', "
                        "and was killed.",
             "url": "https://github.com/romanz/electrs/issues/453"},
        ],
    },
    {
        "id": "rpc-overload",
        "title": "bitcoind RPC overloaded",
        "fault": "bitcoind with -rpcworkqueue=2 -rpcthreads=1, 16 clients calling getblock, and wallets broadcasting through electrs",
        "charts": [{"key": "bitcoind_up", "label": "exporter's RPC to bitcoind succeeding", "kind": "state"},
                   {"key": "rpc_busy_15m", "label": "electrs broadcasts refused as busy, 15m", "kind": "value"},
                   {"key": "rest_errors_5m", "label": "electrs REST error ratio, 5m", "unit": "pct"}],
        "incidents": [
            {"name": "mempool/mempool#4178", "date": "August 2023",
             "summary": "After a code change, the mempool.space backend fetched too many transactions from "
                        "bitcoind at once. Core flooded its log with 'work queue depth exceeded' and sometimes "
                        "aborted.",
             "url": "https://github.com/mempool/mempool/issues/4178"},
            {"name": "bitcoin/bitcoin#7611", "date": "February 2016",
             "summary": "A service calling getrawtransaction from many threads on each new block had its calls "
                        "rejected with 'Work queue depth exceeded' until rpcworkqueue was raised.",
             "url": "https://github.com/bitcoin/bitcoin/issues/7611"},
        ],
    },
    {
        "id": "monitoring-gap",
        "title": "The exporter vanishes",
        "fault": "a Prometheus config that stops scraping bitcoind",
        "charts": [{"key": "exporter_scraped", "label": "bitcoind exporter scraped", "kind": "state"}],
        "incidents": [
            {"name": "GitLab.com database outage", "date": "January 2017",
             "summary": "GitLab's scheduled backups had been failing on every run, and the failure emails were "
                        "silently rejected: 'we were never aware of the backups failing, until it was too late.' "
                        "A check that stops reporting has to be treated as a failure.",
             "url": "https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/"},
            {"name": "Roblox outage", "date": "October 2021",
             "summary": "Roblox's telemetry depended on the Consul cluster that failed, so the team lost "
                        "visibility during a 73-hour outage.",
             "url": "https://about.roblox.com/newsroom/2022/01/roblox-return-to-service-10-28-10-31-2021/"},
        ],
    },
]


# What the drills found, most important first. The page shows them under "What the game day caught".
FINDINGS = [
    {"title": "A node rejecting the network's chain raised no alert",
     "text": "Invalidating the tip on testnet4 moved the node onto a competing fork without a sound. A node that "
             "rejects the chain its peers build on keeps headers equal to blocks, because bitcoind drops headers "
             "that build on an invalid block, so BitcoindBlocksBehindHeaders could never fire. Only the 95-minute "
             "no-new-blocks warning would have, as a ticket. In the drill the node fell 7 blocks behind.",
     "fix": "the exporter now reports the highest invalid chain tip, and the new critical alert "
            "BitcoindRejectedChainAhead paged 10m 44s after the fault."},
    {"title": "A busy bitcoind stopped electrs",
     "text": "When bitcoind's RPC work queue filled up, it answered 503 'Work queue depth exceeded', and electrs "
             "exited: 'server failed: request failed HTTP/1.1 503 Service Unavailable'. electrs waits and retries "
             "when bitcoind is unreachable or still starting, but any other HTTP status is a plain error, which "
             "ends its main loop. A traffic spike on bitcoind becomes an indexer outage.",
     "label": "Patch", "fix": "electrs treats a 503 like a dropped connection and retries (a small change with a "
                              "unit test against a fake bitcoind), ready to send upstream to Blockstream/electrs."},
    {"title": "A fast OOM loop was invisible to the memory and restart alerts",
     "text": "Under a 300 MiB limit electrs was killed 31 times in 8 minutes, each time within seconds of starting "
             "and before Prometheus could scrape it. ElectrsMemoryHigh and ElectrsRestartLoop never had a sample. "
             "Only ElectrsDown paged, after 5m 52s, without saying why.",
     "fix": "BitcoinNodeOOMKilled opens a ticket from the kernel's OOM counter, or from a container's OOMKilled "
            "exit on Kubernetes, so the cause arrives with the page."},
    {"title": "One missing exporter paged twice",
     "text": "With the bitcoind scrape job gone, the job-has-no-target check and the half-a-pair-missing check "
             "both fired with different labels, so Alertmanager sent two pages for one fault.",
     "fix": "the job-level check now fires only when the other job has no targets either. A rerun paged once; "
            "the replay shows the original run with both pages."},
    {"title": "A removed scrape job pages after 10 minutes, not 5",
     "text": "After the config reload Prometheus 3.15.1 kept serving the job's last sample for 5 minutes, so the "
             "alert's 5-minute wait only started after that.",
     "label": "Documented", "fix": "in the bitcoind-down runbook: after a config change, expect the page late and check the change first."},
]


def severities():
    """{alertname: severity} from the rule files (no YAML parser needed for this layout)."""
    out, name = {}, None
    for f in ("rules/bitcoin-node.alerts.yml", "rules/electrs-slo.yml"):
        for line in open(os.path.join(ROOT, f)):
            line = line.strip()
            if line.startswith("- alert:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("severity:") and name:
                out[name] = line.split(":", 1)[1].strip()
                name = None
    return out


def main():
    sev = severities()
    runs = {}
    for path in sys.argv[1:]:
        with open(path) as f:
            d = json.load(f)
        runs[d["scenario"]] = d
    out = []
    for s in SCENARIOS:
        if s["id"] in runs:
            run = runs[s["id"]]
            inject = next((e["t"] for e in run["events"] if e["kind"] == "inject"), 0)
            # A resolved notification for the previous drill can land during this one's baseline.
            run["notifications"] = [n for n in run["notifications"] if n["t"] >= inject or n["status"] == "firing"]
            # The first OOM run could not read the kernel log as this user; the count is in the write-up.
            run["events"] = [e for e in run["events"] if not e["text"].startswith("journal shows")]
            for e in run["events"]:
                if e["kind"] == "ack":
                    head, _, tail = e["text"].partition(" received ")
                    names, _, rest = tail.partition(";")
                    e["text"] = "%s received %s;%s" % (head, ", ".join(dict.fromkeys(names.split(", "))), rest)
            seen = {n for a in run["alerts"] for k in ("pending", "firing", "inhibited") for n in a[k]}
            out.append(dict(s, run=run, severity={n: sev.get(n, "") for n in sorted(seen)}))
    dest = os.path.join(ROOT, "docs/replay/data.js")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        f.write("// Generated by gameday/build_site.py from the game-day recordings. Do not edit.\n")
        f.write("window.GAMEDAY = " + json.dumps(out, separators=(",", ":")) + ";\n")
        f.write("window.GAMEDAY_FINDINGS = " + json.dumps(FINDINGS, separators=(",", ":")) + ";\n")
    print("wrote %s with %d scenarios" % (dest, len(out)))
    print()
    print(markdown_table(out))


def mmss(s):
    return "%dm %02ds" % (s // 60, s % 60)


def markdown_table(out):
    """The results table used in docs/game-day.md and the README, from the same recordings."""
    rows = ["| Drill | Based on | First notification after the fault | Pages | Fix applied | All clear |",
            "|---|---|---|---|---|---|"]
    for s in out:
        run = s["run"]
        inject = next(e["t"] for e in run["events"] if e["kind"] == "inject")
        first = next((n for n in run["notifications"] if n["status"] == "firing"), None)
        pages = sum(1 for n in run["notifications"] if n["status"] == "firing" and n["receiver"] == "page")
        action = next((e["t"] for e in run["events"] if e["kind"] == "action"), None)
        clear = next((e["t"] for e in run["events"] if e["kind"] == "resolved"), None)
        note = "%s %s: %s" % (mmss(first["t"] - inject), first["receiver"],
                              ", ".join(dict.fromkeys(a["alertname"] for a in first["alerts"] if a["status"] == "firing"))) if first else "none"
        src = s["incidents"][0]
        rows.append("| [%s](https://shanurwan.github.io/bitcoin-node-monitoring/#%s) | [%s](%s) | %s | %d | %s | %s |" % (
            s["title"], s["id"], src["name"], src["url"], note, pages,
            "+" + mmss(action - inject) if action is not None else "–",
            "+" + mmss(clear - inject) if clear is not None else "–"))
    return "\n".join(rows)


if __name__ == "__main__":
    main()
