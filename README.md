# bitcoin-node-monitoring

Prometheus alerts, recording rules, a Grafana dashboard and runbooks for running
**bitcoind** with **[Blockstream electrs](https://github.com/Blockstream/electrs)**
(the indexer behind Esplora). It also contains a small bitcoind exporter, because
bitcoind has no Prometheus endpoint.

It is written for the person on call: every alert is meant to be actionable, has a
`for:` duration chosen to avoid flapping, and links to a runbook with triage commands,
likely causes, mitigation, when to escalate, and a handoff note template.

- [What it covers](#what-it-covers)
- [Quickstart](#quickstart)
- [Label conventions](#label-conventions)
- [Alerts](#alerts)
- [Metrics sources](#metrics-sources)
- [Tuning](#tuning)
- [How it was validated](#how-it-was-validated)
- [Repository layout and development](#repository-layout-and-development)

## What it covers

- **Chain health:** bitcoind down, no or few peers, no new blocks, validated chain behind headers, initial block download stalled, node warnings, restart loops.
- **Indexer health:** electrs down, index behind bitcoind, initial sync stalled (without firing during the hours-long full compaction that follows it), main loop stuck, reorg cleanup failing, RocksDB write stops and background errors, mempool sync failures, restart loops.
- **electrs ↔ bitcoind RPC:** rejected or timed-out connections (for example at bitcoind's `-rpcmaxconnections`), busy proxied calls, slow RPC.
- **Serving SLOs:** multi-window, multi-burn-rate alerts for REST availability, REST latency and Electrum latency.
- **Capacity:** electrs memory against a budget you set, file-descriptor exhaustion, data disks filling (via node_exporter).

## Quickstart

### Prometheus on a host

1. Run the exporter next to bitcoind (Python 3.8+, standard library only):

   ```sh
   BITCOIND_RPC_URL=http://127.0.0.1:8332/ \
   BITCOIND_RPC_COOKIE=/var/lib/bitcoind/.cookie \
   EXPORTER_LISTEN=127.0.0.1:9332 \
   python3 -I exporter/bitcoind_exporter.py
   ```

   A hardened systemd unit is in [`examples/bitcoind-exporter.service`](examples/bitcoind-exporter.service).

2. Start electrs with `--monitoring-addr` (for example `127.0.0.1:4224`).

3. Add the scrape jobs and rule files from [`examples/prometheus.yml`](examples/prometheus.yml). The electrs job needs
   `fallback_scrape_protocol: PrometheusText0.0.4`: electrs serves `/metrics` without a `Content-Type` header, and
   Prometheus 3 refuses such targets (`non-compliant scrape target sending blank Content-Type`).

4. Import [`dashboards/bitcoin-node.json`](dashboards/bitcoin-node.json) into Grafana.

5. Set your memory budget for electrs in [`rules/bitcoin-node.rules.yml`](rules/bitcoin-node.rules.yml)
   (`bitcoin_node:electrs_memory_budget_bytes`, 64 GiB by default).

### Kubernetes (prometheus-operator, Flux or plain Kustomize)

```yaml
# kustomization.yaml in your cluster repository
resources:
  - https://github.com/shanurwan/bitcoin-node-monitoring//kubernetes/base?ref=main
  - https://github.com/shanurwan/bitcoin-node-monitoring//kubernetes/exporter?ref=main
```

- `kubernetes/base` is a `PrometheusRule` with every rule in `rules/`, and the dashboard as a ConfigMap labelled
  `grafana_dashboard: "1"` for the Grafana sidecar.
- `kubernetes/exporter` runs the exporter (non-root, read-only root filesystem) against a `bitcoind` Service, reading
  RPC credentials from a Secret named `bitcoind-rpc` (`user`, `password`), and adds `ServiceMonitor`s for the exporter
  and for electrs. Patch the Service selectors, the RPC URL and the `node` label. The electrs ServiceMonitor sets
  `fallbackScrapeProtocol`, which needs prometheus-operator v0.79 or later.

Pin `ref=` to a commit for production.

## Label conventions

The rules join bitcoind and electrs metrics, so the scrape configuration has to label them consistently:

| Label | Value |
|---|---|
| `job` | `bitcoind` for the exporter, `electrs` for electrs, `node` for node_exporter |
| `node` | the same value on all targets of one bitcoind + electrs pair, for example `mainnet-1` |

If your job names differ, either relabel them or replace the `job="..."` selectors in `rules/`.

## Alerts

`critical` is meant to page; `warning` is meant for a ticket or chat channel.

| Alert | Severity | Fires when | Runbook |
|---|---|---|---|
| BitcoindDown | critical | exporter cannot reach bitcoind RPC, or the exporter is not scraped, for 5m | [bitcoind-down](runbooks/bitcoind-down.md) |
| BitcoindNoPeers | critical | zero P2P connections for 10m | [bitcoind-no-peers](runbooks/bitcoind-no-peers.md) |
| BitcoindLowOutboundPeers | warning | fewer than 4 outbound peers for 30m | [bitcoind-low-outbound-peers](runbooks/bitcoind-low-outbound-peers.md) |
| BitcoindNoNewBlocks | critical | height unchanged for 95m outside IBD | [bitcoind-no-new-blocks](runbooks/bitcoind-no-new-blocks.md) |
| BitcoindBlocksBehindHeaders | warning | more than 2 unvalidated headers for 30m outside IBD | [bitcoind-blocks-behind-headers](runbooks/bitcoind-blocks-behind-headers.md) |
| BitcoindInitialBlockDownloadStalled | warning | in IBD and height unchanged for 45m | [bitcoind-initial-block-download-stalled](runbooks/bitcoind-initial-block-download-stalled.md) |
| BitcoindRestartLoop | warning | 3 or more restarts in 1h | [bitcoind-restart-loop](runbooks/bitcoind-restart-loop.md) |
| BitcoindWarnings | warning | `getblockchaininfo` warnings for 15m | [bitcoind-warnings](runbooks/bitcoind-warnings.md) |
| ElectrsDown | critical | electrs not scraped for 5m | [electrs-down](runbooks/electrs-down.md) |
| ElectrsIndexBehind | critical | synced electrs more than 3 blocks behind bitcoind for 10m | [electrs-index-behind](runbooks/electrs-index-behind.md) |
| ElectrsInitialSyncStalled | warning | initial sync, no batch for 45m, RocksDB not compacting | [electrs-initial-sync-stalled](runbooks/electrs-initial-sync-stalled.md) |
| ElectrsMainLoopStalled | critical | main loop counter unchanged for 15m | [electrs-main-loop-stalled](runbooks/electrs-main-loop-stalled.md) |
| ElectrsStaleCleanupFailing | critical | reorg cleanup failing for 10m | [electrs-stale-cleanup-failing](runbooks/electrs-stale-cleanup-failing.md) |
| ElectrsRocksDBWriteStopped | critical | RocksDB stopped writes for 5m | [electrs-rocksdb-write-stopped](runbooks/electrs-rocksdb-write-stopped.md) |
| ElectrsRocksDBBackgroundErrors | critical | any RocksDB background error in 15m | [electrs-rocksdb-background-errors](runbooks/electrs-rocksdb-background-errors.md) |
| ElectrsBitcoindRPCErrors | warning | RPC handshakes rejected/timing out, or proxied calls failing, for 5m | [electrs-bitcoind-rpc-errors](runbooks/electrs-bitcoind-rpc-errors.md) |
| ElectrsBitcoindRPCSlow | warning | bitcoind RPC p99 (excluding `getblock`) above 2.5s for 15m | [electrs-bitcoind-rpc-slow](runbooks/electrs-bitcoind-rpc-slow.md) |
| ElectrsMempoolSyncFailing | warning | more than 2 mempool sync failures in 30m | [electrs-mempool-sync-failing](runbooks/electrs-mempool-sync-failing.md) |
| ElectrsElectrumFdLimit | warning | Electrum connections refused at the fd limit | [electrs-electrum-fd-limit](runbooks/electrs-electrum-fd-limit.md) |
| ElectrsRestartLoop | warning | 3 or more restarts in 1h | [electrs-restart-loop](runbooks/electrs-restart-loop.md) |
| ElectrsMemoryHigh | warning | RSS above 85% of the memory budget for 10m | [electrs-memory-high](runbooks/electrs-memory-high.md) |
| BitcoinNodeDiskWillFill | warning | filesystem full within 48h at the 6h trend, already over 75% used | [bitcoin-node-disk](runbooks/bitcoin-node-disk.md) |
| BitcoinNodeDiskAlmostFull | critical | less than 5% free for 5m | [bitcoin-node-disk](runbooks/bitcoin-node-disk.md) |
| ElectrsRESTAvailabilityBurnFast / Slow | critical / warning | 5xx ratio burning the 99.5% objective | [electrs-rest-availability-slo](runbooks/electrs-rest-availability-slo.md) |
| ElectrsRESTLatencyBurnFast / Slow | critical / warning | requests over 1s burning the 99% objective | [electrs-rest-latency-slo](runbooks/electrs-rest-latency-slo.md) |
| ElectrsElectrumLatencyBurnFast / Slow | critical / warning | calls over 2.5s burning the 99% objective | [electrs-electrum-latency-slo](runbooks/electrs-electrum-latency-slo.md) |

### Design choices worth knowing

- **"No progress" alerts compare with an offset, not `changes()`.** `changes(x[90m]) == 0` is true as soon as Prometheus
  restarts or a target appears, because the window has a single sample. `x - x offset 90m == 0` returns nothing until a
  sample from 90 minutes ago exists, so these alerts cannot fire on a fresh Prometheus.
- **Initial sync is detected from `tip_height == 0`.** electrs sets `tip_height` only when the initial sync, including
  its one-time full compaction, has finished. `initial_sync_progress_pct` is the height of the last batch, not overall
  progress: with `--blocks-dir`, electrs indexes blocks that spend outputs from later blk files at the end, over RPC, so
  the gauge can finish well below 100.
- **The SLO alerts follow the Google SRE workbook** (fast: 14.4x over 1h and 5m, or 6x over 6h and 30m; slow: 3x over
  1d and 2h, or 1x over 3d and 6h) and are suppressed below one request per minute, where ratios are noise.
- **Block timestamps are not used for alerting.** Header times can be two hours off; the "no new blocks" alert uses the
  height instead. The dashboard still shows best-block age.

## Metrics sources

### bitcoind: `exporter/bitcoind_exporter.py`

Existing exporters (for example jvstein/bitcoin-prometheus-exporter) do not expose the header height, the
initial-block-download flag or the best block time, which the chain-health alerts need. This exporter is ~200 lines of
standard-library Python. It sends one JSON-RPC batch (`getblockchaininfo`, `getnetworkinfo`, `getmempoolinfo`,
`getrpcinfo`, `uptime`, `getchaintips`) per scrape, so there is no background polling and no stale cache. It re-reads the
cookie file on every scrape, so bitcoind restarts are picked up.

| Metric | Meaning |
|---|---|
| `bitcoind_up` | 1 if the last RPC batch succeeded |
| `bitcoind_blocks`, `bitcoind_headers` | validated height and header height |
| `bitcoind_initial_block_download`, `bitcoind_verification_progress` | IBD flag and progress |
| `bitcoind_best_block_timestamp_seconds`, `bitcoind_best_block_median_time_seconds` | best block header time, median time past |
| `bitcoind_peers{direction}` | inbound / outbound peers |
| `bitcoind_network_active`, `bitcoind_warnings`, `bitcoind_uptime_seconds`, `bitcoind_pruned` | node state |
| `bitcoind_mempool_transactions`, `_usage_bytes`, `_max_bytes`, `_min_fee_btc_per_kvb`, `_loaded` | mempool |
| `bitcoind_rpc_active_commands` | RPC commands running at scrape time |
| `bitcoind_chain_tips{status}` | chain tips by status (`valid-fork` grows with stale blocks and reorgs) |
| `bitcoind_size_on_disk_bytes`, `bitcoind_info{chain,version,subversion}` | size and version |
| `bitcoind_exporter_rpc_errors_total{method}`, `bitcoind_exporter_scrape_duration_seconds` | exporter health |

### electrs: `--monitoring-addr`

The rules use electrs's own metrics, checked against Blockstream/electrs `new-index` at 4e8e6fe (2026-11-11):
`tip_height`, `initial_sync_height`, `initial_sync_progress_pct`, `electrs_main_loop_count`, `stale_cleanup_failing`,
`rocksdb_*{db}` (per database: `txstore_db`, `history_db`, `cache_db`), `daemon_rpc{method}`,
`daemon_rpc_conn_handshake{result}`, `daemon_rpc_proxied{result}`, `rest_request_duration_seconds{method,route,status}`,
`electrum_rpc{method}`, `electrum_clients`, `electrum_subscriptions`, `electrum_connection_errors_total{reason}`,
`mempool_count{type}`, `mempool_sync_failed_to_index`, `process_memory_rss`, `process_cpu_usage`, `process_fs_fds`.

`daemon_rpc_proxied` only appears after electrs proxies its first RPC call, so on a quiet node that selector has no
series yet; the alert simply does not use that half until it exists.

### Host: node_exporter

The disk alerts use `node_filesystem_avail_bytes` / `node_filesystem_size_bytes` from node_exporter with `job="node"`.

## Tuning

- **Memory budget:** `bitcoin_node:electrs_memory_budget_bytes` in `rules/bitcoin-node.rules.yml`. Size it for the
  initial sync and full compaction, not for steady state.
- **SLO objectives and thresholds:** `SLOS` in `scripts/generate.py`, then run the generator.
- **Thresholds and `for:` durations:** edit `rules/bitcoin-node.alerts.yml`, update the cases in
  `tests/alerts.test.yml`, and run the tests.

## How it was validated

**Unit tests.** `tests/alerts.test.yml` has 36 test groups and 80 evaluations. Every one of the 29 alerts has at least
one case where it must fire and one where it must not, including: a fresh Prometheus with no history (no "no progress"
alerts), a one-block lag while electrs indexes a new block, electrs in initial sync (not "behind"), the post-sync full
compaction (not "stalled"), slow `getblock` calls (ignored), high error ratios on almost no traffic (no page), and
Prometheus 3's normalised `le="1.0"` bucket label. The expected annotations are part of the tests, so a broken template
fails them.

**Live run** on a lab host (12 cores, 30 GB RAM) against testnet4: Bitcoin Core 32.1 (synced, about 161,470 blocks),
electrs built from `new-index` 4e8e6fe with one indexing fix applied, the exporter, and node_exporter, scraped every
15 s by Prometheus 3.15.1, with Grafana 13.3.1.

- All 79 rules loaded and evaluated with `health=ok`. Every recording rule returned data. Every metric selector used by
  the alerts had series, except `daemon_rpc_proxied` (explained above). `scripts/check_live.py` does this check.
- Every dashboard query was run through Grafana's query API with the `node` variable resolved: 41 of 42 returned data,
  none errored, and the empty one is `daemon_rpc_proxied`.
- The exporter's output passes `promtool check metrics`.
- **Induced failures:**
  - Stopping electrs and the exporter at 11:02:14 UTC: `ElectrsDown` and `BitcoindDown` went pending at 11:02:28–30 and
    were firing at 11:07:35.
  - `bitcoin-cli setnetworkactive false` at 11:08:35 UTC: the exporter reported 0 peers, `BitcoindNoPeers` went
    pending at 11:08:45 and was firing by 11:18:46 (its `for:` is 10 minutes). `BitcoindLowOutboundPeers` stayed
    pending, as it needs 30 minutes. After `setnetworkactive true` bitcoind had 5 peers within 30 seconds and the
    alerts cleared.
- Found along the way: Prometheus 3 rejects electrs's metrics endpoint unless the scrape job sets a fallback protocol
  (see the quickstart).

**Measurements behind the memory and compaction guidance** (two full testnet4 initial syncs with default electrs
settings, 17 GB database, `--blocks-dir`): peak RSS 5.8 GiB, during indexing rather than compaction (about 4.1 GiB while
compacting); RocksDB table readers 0.4 GiB at 16 GB of SST files; RocksDB never stopped or delayed writes and recorded
no background errors, so the RocksDB alerts do not fire during a normal sync. Mainnet needs much more memory; electrs
maintainers report using machines with at least 64 GB for a mainnet initial sync and compaction.

## Repository layout and development

```text
exporter/                bitcoind exporter (standard library Python)
rules/                   recording rules, alerts, and generated SLO rules
tests/alerts.test.yml    promtool unit tests
dashboards/              Grafana dashboard (generated)
runbooks/                one runbook per alert
kubernetes/base/         PrometheusRule + dashboard ConfigMap (generated)
kubernetes/exporter/     exporter Deployment, Service, ServiceMonitors
examples/                Prometheus config and systemd unit
scripts/generate.py      generates the SLO rules, PrometheusRule and dashboard
scripts/check_live.py    checks rules and dashboard against a running Prometheus
scripts/lint_dashboard.py  static checks for the dashboard
```

```sh
python3 scripts/generate.py                 # after editing rules or SLOS
promtool check rules rules/*.yml
promtool test rules tests/alerts.test.yml
python3 scripts/lint_dashboard.py
python3 scripts/check_live.py --prometheus http://127.0.0.1:9090 --dashboard dashboards/bitcoin-node.json
```

CI runs all of these except the live check, and fails if generated files are out of date.

## License

Apache-2.0. See [LICENSE](LICENSE).
