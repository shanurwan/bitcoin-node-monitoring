# ElectrsIndexBehind

**Alerts:** `ElectrsIndexBehind`  
**Severity:** critical

electrs has finished its initial sync but has been more than 3 blocks behind bitcoind for 10 minutes.

## Impact

Clients see stale confirmations, balances and fee data; payment flows that wait for confirmations stall.

## Triage

1. Compare heights: `curl -s http://<electrs-http>/blocks/tip/height` and `bitcoin-cli getblockcount`.
2. Is electrs still working? The `ElectrsMainLoopStalled` alert, and its log: each new block logs indexing steps.
3. `stale_cleanup_failing` (after a reorg) and RocksDB write stops can block indexing; check those alerts.
4. RPC health between electrs and bitcoind: the dashboard's RPC panels, `ElectrsBitcoindRPCErrors`.

## Likely causes

- electrs's main loop is blocked (see [electrs-main-loop-stalled](electrs-main-loop-stalled.md)).
- RPC to bitcoind failing or very slow.
- A reorg whose cleanup fails (see [electrs-stale-cleanup-failing](electrs-stale-cleanup-failing.md)).
- RocksDB has stopped writes (disk full, compaction behind).

## Mitigation

Fix the underlying cause from the list. If the process is wedged with no errors, capture a stack (`gdb -p <pid> -batch -ex 'thread apply all bt'`) before restarting it, so the cause can be found.

## Escalate when

Lag keeps growing after a restart, or it is caused by a reorg cleanup failure.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsIndexBehind on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
