# ElectrsMemoryHigh

**Alerts:** `ElectrsMemoryHigh`  
**Severity:** warning

electrs's resident memory has been above 85% of `bitcoin_node:electrs_memory_budget_bytes` for 10 minutes.

## Impact

An OOM kill during initial sync or the full compaction after it restarts a job that takes many hours on mainnet.

## Triage

1. Which phase? `tip_height` = 0 means initial sync; `rocksdb_num_running_compactions` > 0 with the sync done means the one-time full compaction.
2. Dashboard memory panel: RocksDB table readers, memtables and block cache against total RSS.

## Likely causes

Measured on testnet4 (Bitcoin Core 32.1, about 161,000 blocks, default electrs settings, 17 GB database):
- Peak RSS was 5.8 GiB, during indexing, not during compaction (about 4.1 GiB while compacting).
- RocksDB table-reader memory was 0.4 GiB at 16 GB of SST files and grows with the database, unless `--cache-index-filter-blocks` is set.
- Most of the RSS was not covered by RocksDB's own gauges.
Mainnet needs far more; electrs maintainers report using machines with at least 64 GB for mainnet initial sync and compaction.

## Mitigation

- Raise the memory limit for the initial sync and compaction, then lower it for steady state.
- `--cache-index-filter-blocks` moves index and filter blocks into the block cache, which bounds them by `--db-block-cache-mb`. With the default 24 MB cache the testnet4 file import ran about 6 times slower, so raise the cache size along with it.
- If the budget is simply set too low for this host, change `bitcoin_node:electrs_memory_budget_bytes`.

## Escalate when

Memory keeps growing in steady state (after the initial sync and compaction), which suggests a leak.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsMemoryHigh on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
