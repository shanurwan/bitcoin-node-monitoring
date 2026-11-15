# BitcoinNodeDiskWillFill / BitcoinNodeDiskAlmostFull

**Alerts:** `BitcoinNodeDiskWillFill`, `BitcoinNodeDiskAlmostFull`  
**Severity:** warning (will fill) / critical (almost full)

A data filesystem will run out of space within 48 hours at the last 6 hours' growth rate and is over 75% full, or it has less than 5% free.

## Impact

bitcoind shuts down when it cannot write. RocksDB stops writes and may raise background errors; electrs indexing stops.

## Triage

1. `df -h` and `du -sh` of the bitcoind datadir (`blocks/`, `chainstate/`) and the electrs `--db-dir`.
2. Is growth steady (chain growth) or sudden (logs, core dumps, a reindex, compaction)?

## Likely causes

- Normal chain growth outpacing provisioning.
- electrs initial sync and compaction write a lot before old SST files are deleted.
- Logs or core dumps on the same filesystem.

## Mitigation

Grow the volume (most cloud disks and PVCs can be expanded online), move logs off it, or delete core dumps. Do not delete bitcoind or RocksDB files by hand.

## Escalate when

Less than 5% free and the volume cannot be grown quickly.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoinNodeDiskWillFill on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
