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

## Handoff

Use the [handoff note](README.md#handoff-note).
