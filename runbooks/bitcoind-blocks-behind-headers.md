# BitcoindBlocksBehindHeaders

**Alerts:** `BitcoindBlocksBehindHeaders`  
**Severity:** warning

bitcoind has known about more than 2 block headers it has not validated for 30 minutes, outside initial block download.

## Impact

The node and electrs lag the network.

## Triage

1. `bitcoin-cli getblockchaininfo` – how far apart are `headers` and `blocks`, and is the gap shrinking?
2. `debug.log` – look for `UpdateTip` lines (validation progressing) and for stalls or errors.
3. Disk and CPU: `iostat -x 5`, `top`. Validation is I/O bound on slow disks.

## Likely causes

- Slow or saturated disk (validation and the UTXO cache flush).
- Peers do not serve the blocks (rare; bitcoind disconnects stalling peers).
- A block that fails validation: the tip shows as `invalid` in `getchaintips`.

## Mitigation

Give bitcoind I/O headroom (stop competing jobs, raise `-dbcache` if memory allows). If a block is invalid, treat it like a consensus issue, not a performance issue.

## Escalate when

The gap keeps growing for an hour, or a block is marked invalid.

## Handoff

Use the [handoff note](README.md#handoff-note).
