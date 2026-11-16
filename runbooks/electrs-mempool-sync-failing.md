# ElectrsMempoolSyncFailing

**Alerts:** `ElectrsMempoolSyncFailing`  
**Severity:** warning

electrs failed to index fetched mempool transactions more than twice in 30 minutes.

## Impact

Unconfirmed transactions, outspends and fee estimates from electrs may be incomplete.

## Triage

electrs log around the failures; bitcoind RPC health; mempool size (`getmempoolinfo`).

## Likely causes

RPC failures while fetching mempool entries, very large mempools, or transactions that leave the mempool during the sync.

## Mitigation

Usually transient. If persistent, fix RPC health; a restart rebuilds the mempool view.

## Escalate when

It lasts for hours.

## Handoff

Use the [handoff note](README.md#handoff-note).
