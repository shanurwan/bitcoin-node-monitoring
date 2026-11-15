#!/usr/bin/env python3
"""Check the rules and the dashboard against a running Prometheus.

  python3 scripts/check_live.py --prometheus http://127.0.0.1:9090 [--dashboard dashboards/bitcoin-node.json]

For every loaded rule from this repository it reports the rule health, how many series
the expression returns now, and which metric selectors in it have no series at all
(a missing selector usually means a scrape label or job name does not match, or the
metric only appears after the first event of its kind). For the dashboard it runs every
panel query with $node=.* and reports errors and empty results.

Exit status is 1 if any rule is unhealthy or any query errors. Empty results are
reported but are not failures: a healthy node has no firing alerts.
Standard library only.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

OWN_GROUPS = ("bitcoin-node", "bitcoind", "electrs")
# Identifiers that are PromQL keywords or functions, not metric names.
NOT_METRICS = {
    "by", "without", "on", "ignoring", "group_left", "group_right", "and", "or", "unless", "offset", "bool",
    "sum", "max", "min", "count", "avg", "topk", "rate", "increase", "changes", "resets", "time", "vector",
    "histogram_quantile", "predict_linear", "le", "inf", "nan",
}


def get(base, path, **params):
    url = base.rstrip("/") + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def query(base, expr):
    try:
        d = get(base, "/api/v1/query", query=expr)
        return d["data"]["result"], None
    except urllib.error.HTTPError as e:
        return None, json.load(e).get("error", str(e))


def selectors(expr):
    """Metric names used in an expression (recording-rule names included)."""
    expr = re.sub(r'"(?:[^"\\]|\\.)*"', '""', expr)  # drop string literals
    expr = re.sub(r"\b(by|without|on|ignoring|group_left|group_right)\s*\([^)]*\)", " ", expr)
    expr = re.sub(r"\{[^}]*\}", "{}", expr)
    expr = re.sub(r"\[[^\]]*\]", "[]", expr)
    names = set()
    for m in re.finditer(r"(?<![\w:.])([a-zA-Z_:][\w:]*)(?=\s*(\{|\[|\)|$|\s|-|\+|/|\*|>|<|=|!))", expr):
        n = m.group(1)
        if n.lower() in NOT_METRICS or re.fullmatch(r"\d+[smhdwy]", n):
            continue
        names.add(n)
    return sorted(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prometheus", required=True)
    ap.add_argument("--dashboard")
    args = ap.parse_args()
    failed = False

    groups = get(args.prometheus, "/api/v1/rules")["data"]["groups"]
    present = {}

    def has_series(name):
        if name not in present:
            res, err = query(args.prometheus, "count(%s)" % name)
            present[name] = bool(res)
        return present[name]

    print("RULES")
    for g in groups:
        if not g["name"].startswith(OWN_GROUPS):
            continue
        for r in g["rules"]:
            label = r.get("name")
            if r.get("health") != "ok":
                failed = True
            res, err = query(args.prometheus, r["query"])
            if err:
                failed = True
            missing = [n for n in selectors(r["query"]) if not has_series(n)]
            kind = "record" if r["type"] == "recording" else "alert "
            state = "" if r["type"] == "recording" else " state=%s" % r.get("state")
            print("  %s %-48s health=%s series=%s%s%s%s" % (
                kind, label, r.get("health"), "ERR" if err else len(res), state,
                (" missing=" + ",".join(missing)) if missing else "", (" error=" + err) if err else ""))

    if args.dashboard:
        print("DASHBOARD")
        dash = json.load(open(args.dashboard))
        for p in dash["panels"]:
            for t in p.get("targets", []):
                expr = t["expr"].replace("$node", ".*")
                res, err = query(args.prometheus, expr)
                if err:
                    failed = True
                print("  %-55s %-2s series=%s%s" % (p["title"][:55], t["refId"], "ERR" if err else len(res),
                                                    (" error=" + err) if err else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
