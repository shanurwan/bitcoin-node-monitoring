# ElectrsMainLoopStalled

**Alerts:** `ElectrsMainLoopStalled`  
**Severity:** critical

`electrs_main_loop_count`, which goes up every 5 seconds, has not changed for 15 minutes while the process is still scraped.

## Impact

electrs is alive but no longer indexes new blocks or syncs the mempool. Reads still work, so it looks healthy from outside while serving stale data.

## Triage

1. Log: the last lines usually show the step it is stuck in (an RPC call, `indexing`, mempool sync).
2. Stack trace before restarting: `gdb -p <pid> -batch -ex 'thread apply all bt' > electrs-stack.txt`.
3. bitcoind responsiveness: a hung RPC call can block the loop.

## Likely causes

- A blocking RPC call to bitcoind that never returns.
- A long mempool sync on a very large mempool.
- Lock contention or a bug.

## Mitigation

Capture the stack, then restart electrs. If bitcoind was the cause, fix it first.

## Escalate when

It recurs; attach the stack trace and logs to an upstream issue.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsMainLoopStalled on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
