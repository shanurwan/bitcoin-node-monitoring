# ElectrsInitialSyncStalled

**Alerts:** `ElectrsInitialSyncStalled`  
**Severity:** warning

electrs has not finished its initial sync, no block batch has completed for 45 minutes, and RocksDB is not compacting.

## Impact

The node stays unusable. On mainnet an initial sync already takes many hours, so a stall wastes a lot of time.

## Triage

1. electrs log: the last `processing blocks` / `block file reading` lines, and any errors or panics.
2. Is the process using CPU and disk (`top`, `iostat`)? If yes, it may be in a phase the alert cannot see.
3. bitcoind reachable and synced? electrs needs a fully synced bitcoind.

## Likely causes

- Waiting on bitcoind RPC (bitcoind restarting or overloaded).
- With `--blocks-dir`: the file pass finished and electrs is fetching the remaining blocks over RPC. If idle RPC sockets were closed during a long file pass, you see `reconnecting to bitcoind: ... disconnected from daemon while receiving` warnings; electrs reconnects and carries on.
- Memory pressure: the cgroup throttles at its memory.high limit instead of killing the process, and progress crawls.
- Note: `initial_sync_progress_pct` is the height of the last batch, not overall progress. With `--blocks-dir` it can end well below 100 because the RPC fallback indexes low heights last; the alert does not rely on it.

## Mitigation

Fix RPC or memory pressure. Restarting is safe (indexing resumes from what is already stored), but capture the log first.

## Escalate when

No progress for 2 hours with bitcoind healthy and no memory pressure.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsInitialSyncStalled on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
