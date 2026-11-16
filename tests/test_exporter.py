"""Tests for exporter/bitcoind_exporter.py against a fake bitcoind JSON-RPC server.

Run from the repository root:  python3 -m unittest discover -s tests
Standard library only.
"""

import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCKCHAININFO = {
    "chain": "main", "blocks": 870000, "headers": 870001, "bestblockhash": "00" * 32,
    "time": 1731700000, "mediantime": 1731699000, "verificationprogress": 0.9999,
    "initialblockdownload": False, "size_on_disk": 700_000_000_000, "pruned": False, "warnings": [],
}
RESULTS = {
    "getblockchaininfo": BLOCKCHAININFO,
    "getnetworkinfo": {"version": 320100, "subversion": "/Satoshi:32.1.0/", "connections_in": 3,
                       "connections_out": 10, "networkactive": True},
    "getmempoolinfo": {"loaded": True, "size": 1234, "usage": 5_000_000, "maxmempool": 300_000_000,
                       "mempoolminfee": 0.00001},
    "getrpcinfo": {"active_commands": [{"method": "getrpcinfo", "duration": 10}]},
    "uptime": 3600,
    "getchaintips": [{"status": "active"}, {"status": "valid-fork"}, {"status": "valid-fork"}],
}


def ok_replies(batch):
    return [{"id": r["id"], "result": RESULTS[r["method"]], "error": None} for r in batch]


def warmup_replies(batch):
    return [{"id": r["id"], "result": None, "error": {"code": -28, "message": "Loading block index…"}}
            for r in batch]


class FakeBitcoind:
    def __init__(self):
        self.reply = ok_replies
        self.status = 200
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                batch = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(fake.reply(batch)).encode()
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def load_exporter(url):
    os.environ.update(BITCOIND_RPC_URL=url, BITCOIND_RPC_USER="u", BITCOIND_RPC_PASSWORD="p")
    spec = importlib.util.spec_from_file_location("exporter", os.path.join(ROOT, "exporter/bitcoind_exporter.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse(text):
    """{'name{labels}': value} for every sample line."""
    out = {}
    for line in text.decode().splitlines():
        if line and not line.startswith("#"):
            key, value = line.rsplit(" ", 1)
            out[key] = float(value)
    return out


class ExporterTest(unittest.TestCase):
    def setUp(self):
        self.node = FakeBitcoind()
        self.exp = load_exporter(self.node.url)

    def tearDown(self):
        self.node.close()

    def test_healthy_node(self):
        m = parse(self.exp.collect())
        self.assertEqual(m["bitcoind_up"], 1)
        self.assertEqual(m["bitcoind_rpc_warmup"], 0)
        self.assertEqual(m["bitcoind_blocks"], 870000)
        self.assertEqual(m["bitcoind_headers"], 870001)
        self.assertEqual(m['bitcoind_peers{direction="out"}'], 10)
        self.assertEqual(m['bitcoind_chain_tips{status="valid-fork"}'], 2)
        self.assertEqual(m["bitcoind_warnings"], 0)
        self.assertEqual(m["bitcoind_mempool_transactions"], 1234)

    def test_warmup_is_not_up(self):
        # bitcoind answers a batch during warmup with HTTP 200 and -28 per call.
        self.node.reply = warmup_replies
        m = parse(self.exp.collect())
        self.assertEqual(m["bitcoind_up"], 0)
        self.assertEqual(m["bitcoind_rpc_warmup"], 1)
        self.assertNotIn("bitcoind_blocks", m)
        self.assertEqual(m['bitcoind_exporter_rpc_errors_total{method="getblockchaininfo"}'], 1)

    def test_one_failed_method_keeps_the_rest(self):
        def replies(batch):
            out = ok_replies(batch)
            for r in out:
                if batch[r["id"]]["method"] == "getrpcinfo":
                    r.update(result=None, error={"code": -1, "message": "boom"})
            return out
        self.node.reply = replies
        m = parse(self.exp.collect())
        self.assertEqual(m["bitcoind_up"], 1)
        self.assertNotIn("bitcoind_rpc_active_commands", m)
        self.assertEqual(m['bitcoind_exporter_rpc_errors_total{method="getrpcinfo"}'], 1)

    def test_old_string_warnings(self):
        # Bitcoin Core before 28.0 returned warnings as a string.
        def replies(batch):
            out = ok_replies(batch)
            for r in out:
                if batch[r["id"]]["method"] == "getblockchaininfo":
                    r["result"] = dict(BLOCKCHAININFO, warnings="This is a pre-release test build")
            return out
        self.node.reply = replies
        self.assertEqual(parse(self.exp.collect())["bitcoind_warnings"], 1)

    def test_unexpected_reply_shape(self):
        self.node.reply = lambda batch: {"result": None, "error": {"code": -32700, "message": "parse error"}, "id": None}
        m = parse(self.exp.collect())
        self.assertEqual(m["bitcoind_up"], 0)
        self.assertEqual(m['bitcoind_exporter_rpc_errors_total{method="batch"}'], 1)

    def test_http_error(self):
        self.node.status = 401
        self.assertEqual(parse(self.exp.collect())["bitcoind_up"], 0)

    def test_tip_seen_time(self):
        f = self.exp.tip_seen_time
        # First scrape: the header is two hours in the future, so take now.
        self.assertEqual(f("a", 10_000 + 7200, 10_000), 10_000)
        # Same tip later: unchanged.
        self.assertEqual(f("a", 10_000 + 7200, 10_600), 10_000)
        # New tip: when it was seen, whatever its header says.
        self.assertEqual(f("b", 1, 11_000), 11_000)

    def test_tip_seen_time_first_scrape_uses_older_header(self):
        self.assertEqual(self.exp.tip_seen_time("a", 9_000, 10_000), 9_000)


if __name__ == "__main__":
    unittest.main()
