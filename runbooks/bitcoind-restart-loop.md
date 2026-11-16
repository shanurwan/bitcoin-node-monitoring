# BitcoindRestartLoop

**Alerts:** `BitcoindRestartLoop`  
**Severity:** warning

bitcoind's uptime went back to zero at least 3 times in the last hour.

## Impact

Each restart reloads the block index and drops all peers; electrs keeps losing its RPC connections.

## Triage

1. Why does it exit? `debug.log` just before each restart, `journalctl -u bitcoind`, `kubectl describe pod` (OOMKilled, liveness probe).
2. `dmesg | grep -i oom` for OOM kills.

## Likely causes

- OOM kills: `-dbcache` plus mempool plus the OS cache exceed the memory limit.
- A liveness probe that is too strict and kills bitcoind while it is still loading.
- Disk full or a corrupt database causing a crash on startup.

## Mitigation

Lower `-dbcache` or raise the limit; make the probe tolerate startup (a startup probe, or a long initial delay); fix the disk.

## Escalate when

Crashes mention corruption, or the cause is not clear after one restart cycle.

## Handoff

Use the [handoff note](README.md#handoff-note).
