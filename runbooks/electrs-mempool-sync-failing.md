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

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsMempoolSyncFailing on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
