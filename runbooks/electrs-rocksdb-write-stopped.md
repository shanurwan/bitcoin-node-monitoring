# ElectrsRocksDBWriteStopped

**Alerts:** `ElectrsRocksDBWriteStopped`  
**Severity:** critical

RocksDB has stopped writes to one of electrs's databases (txstore, history or cache) for 5 minutes.

## Impact

Indexing and anything that writes to that database block.

## Triage

1. Disk space on the electrs data directory.
2. Dashboard: pending compaction bytes and L0 file counts for that database.
3. electrs log for RocksDB messages.

## Likely causes

- Disk full (RocksDB stops writes when it cannot write SST files).
- Compaction far behind (too many L0 files or pending compaction bytes over the hard limit), often on slow disks.
- In two full testnet4 initial syncs with default settings, writes were never stopped, so this is not expected during a normal sync.

## Mitigation

Free disk space, or give compaction I/O (move to faster storage, raise `--db-parallelism`). Writes resume by themselves once the condition clears.

## Escalate when

It does not clear within 30 minutes with disk space available.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsRocksDBWriteStopped on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
