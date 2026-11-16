# Game day

Six failures injected into a running bitcoind + electrs, each modelled on a public incident, to check that
the alerts page the right person, once, in a predictable time, and that the runbook fixes the problem.

**Replay:** <https://shanurwan.github.io/bitcoin-node-monitoring/> shows each drill in 3D as it was recorded,
with links to the real incidents.

## Setup

- Bitcoin Core 32.1 on testnet4 (outbound peers only), Blockstream electrs (`new-index` 4e8e6fe plus
  Blockstream/electrs#268), `exporter/bitcoind_exporter.py`, node_exporter.
- Prometheus 3.15.1 scraping every 15 s with the rules in `rules/`, and Alertmanager 0.28.1 with
  [`examples/alertmanager.yml`](../examples/alertmanager.yml), whose page and ticket webhooks point at the recorder.
- `scripts/electrs_traffic.py` sending about 4 REST requests and 3 Electrum calls a second throughout.
- [`gameday/gameday.py`](../gameday/gameday.py) ran each drill: one minute of baseline, the fault, then the
  on-call loop. When the first page or ticket arrived it waited two minutes (ack, open the runbook), applied
  the runbook's mitigation, and waited until every alert had resolved and the resolved notifications had
  been sent. Every 5 seconds it recorded key metrics and alert states from Prometheus, and which alerts
  Alertmanager was holding back. Every notification Alertmanager sent was recorded as it arrived.

The recordings are in [`docs/replay/`](replay/). `gameday/build_site.py` bundles them for the replay page.

## Results

| Drill | Based on | First notification after the fault | Pages | Fix applied | All clear |
|---|---|---|---|---|---|
| [bitcoind crashes](https://shanurwan.github.io/bitcoin-node-monitoring/#bitcoind-crash) | [CVE-2018-17144](https://bitcoincore.org/en/2018/09/20/notice/) | 5m 29s page: BitcoindDown | 1 | +7m 29s | +8m 04s |
| [Node rejects the network's chain](https://shanurwan.github.io/bitcoin-node-monitoring/#consensus-split) | [BIP 50: the March 2013 chain fork](https://github.com/bitcoin/bips/blob/master/bip-0050.mediawiki) | 10m 44s page: BitcoindRejectedChainAhead | 1 | +12m 44s | +19m 19s |
| [Node cut off from its peers](https://shanurwan.github.io/bitcoin-node-monitoring/#network-isolation) | [bitcoin/bitcoin#48](https://github.com/bitcoin/bitcoin/issues/48) | 10m 39s page: BitcoindNoPeers | 1 | +12m 39s | +14m 39s |
| [electrs killed for memory](https://shanurwan.github.io/bitcoin-node-monitoring/#electrs-oom) | [Blockstream/electrs#215](https://github.com/Blockstream/electrs/issues/215) | 5m 52s page: ElectrsDown | 1 | +7m 52s | +9m 55s |
| [bitcoind RPC overloaded](https://shanurwan.github.io/bitcoin-node-monitoring/#rpc-overload) | [mempool/mempool#4178](https://github.com/mempool/mempool/issues/4178) | 6m 04s page: ElectrsDown | 1 | +8m 04s | +10m 05s |
| [The exporter vanishes](https://shanurwan.github.io/bitcoin-node-monitoring/#monitoring-gap) | [GitLab.com database outage](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/) | 10m 33s page: BitcoindDown | 2 | +12m 33s | +14m 34s |

Times are from the fault. *Fix applied* includes the two minutes the script waited before acting. The exporter
drill's two pages are the double page found by the drill and since fixed; the rerun with the fix paged once.

## Findings

### 1. A node rejecting the network's chain raised no alert

`bitcoin-cli invalidateblock` on the tip models a node that refuses blocks the rest of the network accepts: the
0.7 nodes in March 2013 ([BIP 50](https://github.com/bitcoin/bips/blob/master/bip-0050.mediawiki)), or a node
that ran out of disk and marked a valid block invalid ([bitcoin/bitcoin#26112](https://github.com/bitcoin/bitcoin/issues/26112)).

- The first try showed nothing at all. testnet4 had a competing block at the same height, the node switched to
  it, and no metric changed. It took three invalidations to leave the node below the network's chain.
- `headers` stayed equal to `blocks` for the whole drill. bitcoind drops headers that build on an invalid block,
  so `BitcoindBlocksBehindHeaders` could never fire. The only other signal was `BitcoindNoNewBlocks` after 95
  minutes, and that is a warning.
- The node also dropped the peers that sent it the rejected chain. `BitcoindLowOutboundPeers` went pending.
- By the time `reconsiderblock` ran, the network was 7 blocks ahead. The node caught up within about 3 minutes.

**Fixed:** the exporter reports `bitcoind_invalid_tip_height` (the highest chain tip the node marked invalid),
and `BitcoindRejectedChainAhead` (critical) fires when that is above the node's own height for 10 minutes. It
paged 10m 44s after the fault. Runbook: [bitcoind-rejected-chain-ahead](../runbooks/bitcoind-rejected-chain-ahead.md).

### 2. A fast OOM loop was invisible to the memory and restart alerts

electrs restarted under `MemoryMax=300M` with no swap. Its steady-state RSS is about 930 MiB. The kernel log
shows 31 `Memory cgroup out of memory: Killed process (electrs)` lines in 8 minutes, the first 4 seconds after
the restart. electrs never stayed up long enough to answer a scrape, so `ElectrsMemoryHigh` and
`ElectrsRestartLoop` had no samples. `ElectrsDown` paged after 5m 52s, without saying why.

**Fixed:** `BitcoinNodeOOMKilled` (warning) fires on any increase of node_exporter's `node_vmstat_oom_kill`, or
on a bitcoind or electrs container that restarted after an `OOMKilled` exit. On this host the counter had not
moved in the two days before the drill, so it is quiet in normal running.

### 3. One missing exporter paged twice

With the bitcoind scrape job removed, `BitcoindDown` fired twice: once from `absent(up{job="bitcoind"})`, with
only a `job` label, and once from the check for a node whose electrs has no bitcoind, with a `node` label.
Alertmanager groups by `alertname` and `node`, so it sent two pages for one fault.

**Fixed:** the `absent()` branch of `BitcoindDown` and `ElectrsDown` now fires only when the other job has no
targets either. If it does, the per-node check already names the node. A rerun of the drill with the fix paged once, 10m 28s after
the change. The replay shows the original run, with both pages.

### 4. A removed scrape job pages after 10 minutes, not 5

After the reload, `up{job="bitcoind"}` kept returning the last sample for 5 minutes. Prometheus 3.15.1 did not
mark the removed job's series stale. The alert's own 5 minutes started only after that, so the page came
10m 33s after the change.

**Documented** in the [bitcoind-down](../runbooks/bitcoind-down.md) runbook: after a config change, expect the
page late and check the change first.

### 5. A busy bitcoind stopped electrs

bitcoind restarted with `-rpcworkqueue=2 -rpcthreads=1` while 16 clients called `getblock`, modelled on
[mempool/mempool#4178](https://github.com/mempool/mempool/issues/4178), where a backend fetching too much at once
filled bitcoind's work queue. Of 347,627 flood calls, 112,009 were rejected. electrs exited 19 seconds in:

```text
ERROR server failed: Error: request failed "HTTP/1.1 503 Service Unavailable": ... = "Work queue depth exceeded"
```

In `src/daemon.rs`, `into_jsonrpc_body` accepts HTTP 200 and 500 and turns every other status into a plain error.
`retry_request` retries connection errors and warmup (-28) only, so the 503 reached the main loop, which exits.
A burst of load on bitcoind turned into an indexer outage that needed a person to restart electrs.
`ElectrsDown` paged 6m 04s after the fault, and the runbook (restore bitcoind's work queue, then start electrs)
fixed it.

**Patch:** treat a 503 like a dropped connection, so electrs waits, reconnects and retries, as it already does
during warmup. A unit test against a fake bitcoind fails without the change, with the same error as above, and
passes with it. All 39 daemon tests pass. The patch is ready to send to Blockstream/electrs.

## Notes on the runs

- Each drill starts only when no alert is pending or firing. Between some drills that took a while, because
  `BitcoindRestartLoop` (3 restarts in an hour) correctly fired after the drills restarted bitcoind.
- The first RPC-overload run was discarded. The script took a stale `bitcoind_up` sample as bitcoind being back,
  and started the flood before RPC answered. It now checks RPC directly.
- `ElectrsMainLoopStalled` and `ElectrsBitcoindRPCErrors` stayed quiet while bitcoind was down, as designed. No
  drill needed Alertmanager's inhibit rules, because the rules already suppress those symptoms. The inhibit
  rules are a second layer for alerts the rules do not suppress, such as the SLO burn alerts during a long
  bitcoind outage.

## Not run live

- **Disk full** (bitcoin/bitcoin#26112). The lab user has no root, and the data disk is shared with other
  work, so there was no safe volume to fill. `BitcoinNodeDiskAlmostFull`, `BitcoinNodeDiskWillFill` and the
  PVC alerts are covered by the rule tests only. That incident ended with the node marking a valid block
  invalid and stopping below the network's tip. The consensus-split drill tests that end state.
- **Long warmup** (bitcoin/bitcoin#11600). On this testnet4 node bitcoind answered RPC 14 seconds after a
  restart, too quickly to test `BitcoindWarmupTooLong` (30 minutes). The crash drill shows that a normal
  warmup does not page. The exporter tests cover the -28 replies themselves.

## Run it yourself

The drills drive user systemd units on the lab host. `LAB` at the top of `gameday/gameday.py` holds the
commands and ports. Change it for your own setup, then:

```sh
python3 gameday/gameday.py bitcoind-crash --out docs/replay/bitcoind-crash.json
python3 gameday/build_site.py docs/replay/*.json
python3 -m http.server -d docs 8000      # open http://127.0.0.1:8000/
```

Only run it against a node nobody depends on: every drill takes something down on purpose.
