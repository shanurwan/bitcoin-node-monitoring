# ElectrsMainLoopStalled

**Alerts:** `ElectrsMainLoopStalled`  
**Severity:** critical

`electrs_main_loop_count`, which goes up every 5 seconds, has not changed for 15 minutes while the process is still
scraped. The alert is suppressed while `bitcoind_up` is 0 for the same node: electrs retries forever while bitcoind
is unreachable or warming up, and `BitcoindDown` or `BitcoindWarmupTooLong` already covers that.

## Impact

electrs is alive but no longer indexes new blocks or syncs the mempool. Reads still work, so it looks healthy from outside while serving stale data.

## Triage

1. Log: the last lines usually show the step it is stuck in (an RPC call, `indexing`, mempool sync).
2. Stack trace before restarting: `gdb -p <pid> -batch -ex 'thread apply all bt' > electrs-stack.txt`.
3. bitcoind as electrs sees it: the exporter may reach bitcoind while electrs cannot (a different address, a stale
   cookie, `-rpcwhitelist`, or `-rpcmaxconnections` reached). Look for `reconnecting to bitcoind` or
   `bitcoind is warming up` repeating in the electrs log, and at the RPC handshake panel.

## Likely causes

- electrs waiting on bitcoind: its main-loop RPC calls retry every 3 s, forever, on connection errors and on error
  -28, so any bitcoind problem electrs sees and the exporter does not stops the loop.
- A blocking RPC call to bitcoind that never returns.
- A long mempool sync on a very large mempool.
- Lock contention or a bug.

## Mitigation

Capture the stack, then restart electrs. If bitcoind was the cause, fix it first.

## Escalate when

It recurs; attach the stack trace and logs to an upstream issue.

## Handoff

Use the [handoff note](README.md#handoff-note).
