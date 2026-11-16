#!/usr/bin/env python3
"""Send light REST and Electrum traffic to an electrs, for checking the serving panels and SLO rules.

  python3 scripts/electrs_traffic.py --rest http://127.0.0.1:3000 --electrum 127.0.0.1:50001 [--interval 2]

electrs creates its per-route and per-method latency histograms on the first request of
each kind, so on a node nobody queries, the REST and Electrum panels and the SLO recording
rules have no data. Each round picks a random block, fetches it and one of its transactions
and addresses over REST, asks for a missing transaction (a 4xx), and opens an Electrum
connection that subscribes to headers and fetches a block header and a fee estimate. Up to
five Electrum connections stay open, so electrum_clients is not always zero.

Only use it against your own electrs. Standard library only.
"""

import argparse
import json
import random
import socket
import sys
import time
import urllib.error
import urllib.request


def rest(base, path):
    try:
        with urllib.request.urlopen(base.rstrip("/") + path, timeout=10) as r:
            return r.read()
    except (urllib.error.URLError, OSError):
        return None


def electrum_session(addr, height):
    host, _, port = addr.rpartition(":")
    sock = socket.create_connection((host, int(port)), timeout=15)
    f = sock.makefile("rwb")
    calls = [("server.version", ["electrs-traffic", "1.4"]), ("blockchain.headers.subscribe", []),
             ("blockchain.block.header", [height]), ("blockchain.estimatefee", [6])]
    for i, (method, params) in enumerate(calls):
        f.write((json.dumps({"id": i, "method": method, "params": params}) + "\n").encode())
        f.flush()
        json.loads(f.readline())
    return sock


def round_trip(args, open_sockets):
    tip = int(rest(args.rest, "/blocks/tip/height") or 0)
    height = random.randint(1, tip) if tip else 0
    block = (rest(args.rest, "/block-height/%d" % height) or b"").decode()
    txids = json.loads(rest(args.rest, "/block/%s/txids" % block) or b"[]") if block else []
    if txids:
        tx = json.loads(rest(args.rest, "/tx/" + random.choice(txids)) or b"{}")
        for out in tx.get("vout", [])[:2]:
            if out.get("scriptpubkey_address"):
                rest(args.rest, "/address/%s/txs" % out["scriptpubkey_address"])
    rest(args.rest, "/mempool")
    rest(args.rest, "/fee-estimates")
    rest(args.rest, "/tx/" + "00" * 32)  # not found
    try:
        open_sockets.append(electrum_session(args.electrum, height))
    except (OSError, ValueError) as e:
        print("electrum: %s" % e, file=sys.stderr)
    while len(open_sockets) > 5:
        open_sockets.pop(0).close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rest", default="http://127.0.0.1:3000", help="electrs --http-addr as a URL")
    ap.add_argument("--electrum", default="127.0.0.1:50001", help="electrs --electrum-rpc-addr")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between rounds")
    ap.add_argument("--rounds", type=int, default=0, help="stop after this many rounds (0: run until stopped)")
    args = ap.parse_args()
    open_sockets, n = [], 0
    while not args.rounds or n < args.rounds:
        round_trip(args, open_sockets)
        n += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
