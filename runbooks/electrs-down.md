# ElectrsDown

**Alerts:** `ElectrsDown`  
**Severity:** critical

Prometheus has not been able to scrape electrs's monitoring endpoint for 5 minutes, or has no electrs target at all
(for one node whose bitcoind is scraped, or for every node).

## Impact

The monitoring endpoint starts at process start, before indexing, so this almost always means electrs is not running: REST and Electrum clients get connection errors.

## Triage

1. Process state: `systemctl status electrs` / `kubectl get pod`, and the last lines of its log. If there is no
   target, check that the pod exists and is not Pending, that the Service selects it, and that the ServiceMonitor
   matches the Service and the pod has the `bitcoin-node` label.
2. If the log ends in a panic, note the message and location. For example, the initial sync from `--blocks-dir`
   panics with `MissingTxo(...)` at `src/new_index/schema.rs` when a block spends an output stored in a later blk
   file, because blk*.dat files hold blocks in download order (Blockstream/electrs#214).
3. OOM kill? `dmesg | grep -i oom`, `kubectl describe pod` (Last State: OOMKilled). Initial sync and the full compaction after it are the memory peaks.
4. If the process is running, check the scrape itself: Prometheus 3 rejects electrs's endpoint unless the job sets `fallback_scrape_protocol: PrometheusText0.0.4` (electrs sends no Content-Type header); the target page then shows `non-compliant scrape target`.

## Likely causes

- Panic during indexing (see above).
- Not scheduled: pod Pending (no node in the zone of its persistent disk, or no capacity), or scaled to 0.
- OOM kill during initial sync or compaction (see [electrs-memory-high](electrs-memory-high.md)).
- bitcoind unreachable at startup: electrs exits if it cannot connect.
- Scrape configuration, not electrs (wrong port, missing fallback protocol).

## Mitigation

- Panic in blk-file import (#214): restart with `--jsonrpc-import` instead of `--blocks-dir`. The partially built
  database can be kept; the import resumes. Blockstream/electrs#268 (not merged at the time of writing) makes the
  file import defer such blocks to RPC instead of panicking.
- OOM: raise the memory limit for the initial sync, or set `--db-block-cache-mb` with `--cache-index-filter-blocks` to bound table-reader memory (slower).
- bitcoind: fix it first ([bitcoind-down](bitcoind-down.md)), then restart electrs.

## Escalate when

It crashes again after a restart with the same panic, or the database fails to open (corruption means a resync that takes many hours on mainnet).

## Handoff

Use the [handoff note](README.md#handoff-note).
