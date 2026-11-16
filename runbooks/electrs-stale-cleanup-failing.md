# ElectrsStaleCleanupFailing

**Alerts:** `ElectrsStaleCleanupFailing`  
**Severity:** critical

electrs reports (`stale_cleanup_failing` = 1) that removing history from blocks that left the best chain is failing; indexing cannot advance until it succeeds.

## Impact

electrs stays at the height before the reorg; ElectrsIndexBehind follows.

## Triage

1. electrs log around the reorg: the error from the cleanup and its retries. Retries back off, and run again at
   once when the tip changes.
2. `bitcoin-cli getchaintips` to see the reorg depth.
3. Disk space and RocksDB errors.

## Likely causes

- A stale block that bitcoind never downloaded or no longer serves: electrs needs the stale block's transactions to
  remove their history. (A pruned bitcoind is not the cause: electrs refuses to start against one.)
- A reorg deeper than expected.
- RocksDB write errors (disk full, background errors).

## Mitigation

Fix disk or RocksDB problems. electrs retries the cleanup with a backoff, and immediately when a new block arrives,
so it clears by itself once the cause is gone. If bitcoind cannot provide the stale block, electrs may need a
resync.

## Escalate when

Immediately if it does not clear within 30 minutes: this may need a resync, which takes hours.

## Handoff

Use the [handoff note](README.md#handoff-note).
