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
- With `--blocks-dir`: the file pass finished and electrs is fetching the remaining blocks over RPC. If idle RPC
  sockets were closed during a long file pass, you see `reconnecting to bitcoind: ... disconnected from daemon while
  receiving` warnings; electrs reconnects and carries on.
- Memory pressure: the cgroup throttles at its memory.high limit instead of killing the process, and progress crawls.
- Note: `initial_sync_progress_pct` is derived from the height of the last batch, not from overall progress, so the
  alert does not rely on it. With the change in Blockstream/electrs#268 (not merged at the time of writing),
  `--blocks-dir` defers blocks whose inputs are in later blk files and indexes them over RPC at the end, so the
  gauge can finish below 100.

## Mitigation

Fix RPC or memory pressure. Restarting is safe (indexing resumes from what is already stored), but capture the log first.

## Escalate when

No progress for 2 hours with bitcoind healthy and no memory pressure.

## Handoff

Use the [handoff note](README.md#handoff-note).
