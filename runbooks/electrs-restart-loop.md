# ElectrsRestartLoop

**Alerts:** `ElectrsRestartLoop`  
**Severity:** warning

electrs's CPU-time counter went back to zero at least 3 times in an hour: the process keeps restarting.

## Impact

Each restart drops all Electrum clients, and a restart during initial sync loses the work since the last saved batch.

## Triage

1. Exit reason from the log just before each start, `kubectl describe pod` (OOMKilled, probe failures), `dmesg`.
2. Probes: electrs only opens REST and Electrum after the initial sync, so a liveness probe on those ports kills it during the sync.

## Likely causes

- Panic on startup or during indexing (for example #214 with `--blocks-dir`).
- OOM kills.
- Liveness probe on the REST/Electrum port during initial sync.

## Mitigation

Fix the cause; probe the monitoring port (or use a startup probe with a long budget) until the initial sync completes.

## Escalate when

The same panic repeats.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsRestartLoop on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
