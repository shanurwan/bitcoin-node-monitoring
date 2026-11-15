# ElectrsElectrumLatencyBurnFast / ElectrsElectrumLatencyBurnSlow

**Alerts:** `ElectrsElectrumLatencyBurnFast`, `ElectrsElectrumLatencyBurnSlow`  
**Severity:** critical (fast) / warning (slow)

More than 1% of Electrum RPC calls take longer than 2.5 s, fast enough to use up the 30-day budget early.

## Impact

Electrum wallets sync slowly or time out.

## Triage

1. Which window fired? Fast burn (critical) means the budget would be gone within days; slow burn (warning) within weeks.
2. Dashboard "electrs serving" row: which routes or methods produce the bad requests, and since when.
3. Correlate with deploys, ElectrsIndexBehind, RPC alerts and host load.
4. `electrum_rpc` latency by `method`: `blockchain.scripthash.get_history` on large wallets is the usual one.

## Likely causes

Large wallets or many subscriptions per connection, mempool churn, disk contention.

## Mitigation

Limit expensive clients, add replicas, or move competing I/O away.

## Escalate when

Fast burn continues for 30 minutes after mitigation.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsElectrumLatencyBurnFast on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
