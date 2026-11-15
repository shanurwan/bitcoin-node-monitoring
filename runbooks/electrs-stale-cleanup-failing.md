# ElectrsStaleCleanupFailing

**Alerts:** `ElectrsStaleCleanupFailing`  
**Severity:** critical

electrs reports (`stale_cleanup_failing` = 1) that removing history from blocks that left the best chain is failing; indexing cannot advance until it succeeds.

## Impact

electrs stays at the height before the reorg; ElectrsIndexBehind follows.

## Triage

1. electrs log around the reorg: the error from the cleanup and its retries.
2. `bitcoin-cli getchaintips` to see the reorg depth.
3. Disk space and RocksDB errors.

## Likely causes

- A reorg deeper than expected, or blocks bitcoind no longer has (pruned bitcoind).
- RocksDB write errors (disk full, background errors).

## Mitigation

Fix disk or RocksDB problems; electrs retries the cleanup on every loop. If bitcoind is pruned below the reorg point, electrs may need a resync.

## Escalate when

Immediately if it does not clear within 30 minutes: this may need a resync, which takes hours.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsStaleCleanupFailing on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
