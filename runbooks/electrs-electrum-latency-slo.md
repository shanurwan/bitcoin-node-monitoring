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

## Handoff

Use the [handoff note](README.md#handoff-note).
