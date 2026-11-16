# ElectrsRocksDBWriteStopped

**Alerts:** `ElectrsRocksDBWriteStopped` (critical), `ElectrsRocksDBWriteDelayed` (warning)  
**Severity:** critical / warning

RocksDB has stopped writes to one of electrs's databases (txstore, history or cache) for 5 minutes, or, after the
initial sync, has throttled them (`rocksdb_actual_delayed_write_rate` > 0) for 15 minutes. Delays come first; a stop
follows if compaction keeps falling behind.

## Impact

Indexing and anything that writes to that database block.

## Triage

1. Disk space on the electrs data directory.
2. Dashboard: the "RocksDB L0 files", "RocksDB compaction" (pending bytes) and "RocksDB delayed write rate" panels
   for that database.
3. electrs log for RocksDB messages.

## Likely causes

- Disk full (RocksDB stops writes when it cannot write SST files).
- Compaction far behind (too many L0 files or pending compaction bytes over the hard limit), often on slow disks.
- In two full testnet4 initial syncs with default settings, writes were never stopped, so this is not expected during a normal sync.

## Mitigation

Free disk space, or give compaction I/O (move to faster storage, raise `--db-parallelism`). Writes resume by themselves once the condition clears.

## Escalate when

It does not clear within 30 minutes with disk space available.

## Handoff

Use the [handoff note](README.md#handoff-note).
