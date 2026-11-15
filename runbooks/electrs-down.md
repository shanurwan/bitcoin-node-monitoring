# ElectrsDown

**Alerts:** `ElectrsDown`  
**Severity:** critical

Prometheus has not been able to scrape electrs's monitoring endpoint for 5 minutes.

## Impact

The monitoring endpoint starts at process start, before indexing, so this almost always means electrs is not running: REST and Electrum clients get connection errors.

## Triage

1. Process state: `systemctl status electrs` / `kubectl get pod`, and the last lines of its log.
2. If the log ends in a panic, note the message and location. For example, indexing from `--blocks-dir` panicked with `MissingTxo(...)` at `src/new_index/schema.rs` on fresh nodes because blk*.dat files hold blocks in download order (Blockstream/electrs#214).
3. OOM kill? `dmesg | grep -i oom`, `kubectl describe pod` (Last State: OOMKilled). Initial sync and the full compaction after it are the memory peaks.
4. If the process is running, check the scrape itself: Prometheus 3 rejects electrs's endpoint unless the job sets `fallback_scrape_protocol: PrometheusText0.0.4` (electrs sends no Content-Type header); the target page then shows `non-compliant scrape target`.

## Likely causes

- Panic during indexing (see above).
- OOM kill during initial sync or compaction (see [electrs-memory-high](electrs-memory-high.md)).
- bitcoind unreachable at startup: electrs exits if it cannot connect.
- Scrape configuration, not electrs (wrong port, missing fallback protocol).

## Mitigation

- Panic in blk-file import (#214): restart with `--jsonrpc-import` instead of `--blocks-dir`, or run a build that defers those blocks to RPC. The partially built database can be kept; the import resumes.
- OOM: raise the memory limit for the initial sync, or set `--db-block-cache-mb` with `--cache-index-filter-blocks` to bound table-reader memory (slower).
- bitcoind: fix it first ([bitcoind-down](bitcoind-down.md)), then restart electrs.

## Escalate when

It crashes again after a restart with the same panic, or the database fails to open (corruption means a resync that takes many hours on mainnet).

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsDown on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
