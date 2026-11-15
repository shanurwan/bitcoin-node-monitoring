# ElectrsElectrumFdLimit

**Alerts:** `ElectrsElectrumFdLimit`  
**Severity:** warning

electrs refused Electrum connections because it is close to its open-file limit.

## Impact

New Electrum clients cannot connect.

## Triage

1. `electrum_clients` and `process_fs_fds` on the dashboard; the process limit (`cat /proc/<pid>/limits`).
2. Are clients leaking connections or is it a traffic spike?

## Likely causes

`LimitNOFILE` / ulimit too low for the client count (RocksDB also keeps many files open), or a client opening connections in a loop.

## Mitigation

Raise the open-file limit (`LimitNOFILE=` in systemd, or the container runtime's limit), and rate-limit abusive clients at the proxy.

## Escalate when

The limit is already high and connections keep growing.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsElectrumFdLimit on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
