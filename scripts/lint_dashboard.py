#!/usr/bin/env python3
"""Static checks for dashboards/*.json. Standard library only.

- valid JSON with a uid and title
- unique panel ids, panels inside the 24-column grid, no overlapping panels
- every query panel uses the ${datasource} variable and has at least one target
- every target has an expr, a unique refId within its panel, and balanced brackets
- every metric or recording-rule name used is produced by the exporter, electrs,
  node_exporter, Prometheus itself or the rules in rules/
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Metrics electrs exposes (checked against electrs new-index 4e8e6fe, see README).
ELECTRS = {
    "tip_height", "initial_sync_height", "initial_sync_progress_pct", "electrs_main_loop_count",
    "stale_cleanup_failing", "process_memory_rss", "process_cpu_usage", "process_fs_fds",
    "rest_request_duration_seconds_bucket", "rest_request_duration_seconds_count", "rest_requests_in_flight",
    "electrum_rpc_bucket", "electrum_rpc_count", "electrum_clients", "electrum_subscriptions",
    "electrum_connection_errors_total", "daemon_rpc_bucket", "daemon_rpc_count", "daemon_rpc_conn_handshake",
    "daemon_rpc_proxied", "mempool_count", "mempool_sync_failed_to_index",
}
NODE_EXPORTER = {"node_filesystem_avail_bytes", "node_filesystem_size_bytes"}
PROMETHEUS = {"up", "ALERTS"}
KEYWORDS = {"by", "without", "on", "ignoring", "group_left", "group_right", "and", "or", "unless", "offset",
            "sum", "max", "min", "count", "avg", "topk", "rate", "increase", "histogram_quantile", "vector",
            "time", "le"}


def known_names():
    names = set(ELECTRS) | NODE_EXPORTER | PROMETHEUS
    src = open(os.path.join(ROOT, "exporter", "bitcoind_exporter.py")).read()
    names |= set(re.findall(r'm\.add\("([a-z_]+)"', src))
    for p in glob.glob(os.path.join(ROOT, "rules", "*.yml")):
        names |= set(re.findall(r"record: ([\w:]+)", open(p).read()))
    # rocksdb_* gauges are generated per property by electrs.
    return names


def used_names(expr):
    e = re.sub(r'"(?:[^"\\]|\\.)*"', '""', expr)
    e = re.sub(r"\b(by|without|on|ignoring|group_left|group_right)\s*\([^)]*\)", " ", e)
    e = re.sub(r"\{[^}]*\}", "{}", e)
    e = re.sub(r"\[[^\]]*\]", "[]", e)
    out = set()
    for m in re.finditer(r"(?<![\w:.$])([a-zA-Z_:][\w:]*)(?![\w:])(?!\s*\()", e):
        n = m.group(1)
        if n not in KEYWORDS and not re.fullmatch(r"\d+[smhdwy]", n):
            out.add(n)
    return out


def balanced(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in re.sub(r'"(?:[^"\\]|\\.)*"', '""', s):
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def lint(path, known):
    errs = []
    d = json.load(open(path))
    for k in ("uid", "title", "panels"):
        if not d.get(k):
            errs.append("missing %s" % k)
    ids = set()
    cells = {}
    for p in d["panels"]:
        pid = p.get("id")
        if pid in ids:
            errs.append("duplicate panel id %s" % pid)
        ids.add(pid)
        g = p["gridPos"]
        if g["x"] < 0 or g["x"] + g["w"] > 24:
            errs.append("panel %r outside the grid" % p["title"])
        for x in range(g["x"], g["x"] + g["w"]):
            for y in range(g["y"], g["y"] + g["h"]):
                if (x, y) in cells:
                    errs.append("panel %r overlaps %r" % (p["title"], cells[(x, y)]))
                    break
                cells[(x, y)] = p["title"]
        if p["type"] == "row":
            continue
        if p.get("datasource", {}).get("uid") != "${datasource}":
            errs.append("panel %r does not use ${datasource}" % p["title"])
        if not p.get("targets"):
            errs.append("panel %r has no targets" % p["title"])
        refs = set()
        for t in p.get("targets", []):
            if t["refId"] in refs:
                errs.append("panel %r duplicate refId %s" % (p["title"], t["refId"]))
            refs.add(t["refId"])
            expr = t.get("expr", "")
            if not expr or not balanced(expr):
                errs.append("panel %r refId %s: empty or unbalanced expr" % (p["title"], t["refId"]))
            for n in used_names(expr):
                if n not in known and not n.startswith("rocksdb_"):
                    errs.append("panel %r uses unknown metric %s" % (p["title"], n))
    return errs


def main():
    known = known_names()
    failed = False
    for path in sorted(glob.glob(os.path.join(ROOT, "dashboards", "*.json"))):
        errs = lint(path, known)
        print("%s: %s" % (os.path.relpath(path, ROOT), "ok" if not errs else "%d problem(s)" % len(errs)))
        for e in errs:
            print("  " + e)
        failed |= bool(errs)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
