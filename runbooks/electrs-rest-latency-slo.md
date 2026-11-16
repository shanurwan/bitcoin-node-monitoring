# ElectrsRESTLatencyBurnFast / ElectrsRESTLatencyBurnSlow

**Alerts:** `ElectrsRESTLatencyBurnFast`, `ElectrsRESTLatencyBurnSlow`  
**Severity:** critical (fast) / warning (slow)

More than 1% of REST requests take longer than 1 s, fast enough to use up the 30-day budget early.

## Impact

Explorers and wallets feel slow or time out.

## Triage

1. Which window fired? Fast burn (critical) means the budget would be gone within days; slow burn (warning) within weeks.
2. Dashboard "electrs serving" row: which routes or methods produce the bad requests, and since when.
3. Correlate with deploys, ElectrsIndexBehind, RPC alerts and host load.
4. Address history routes on very busy addresses are the usual slow ones; check `rest_request_duration_seconds` by `route`.

## Likely causes

Heavy address-history queries, a cold cache after restart, disk I/O contention (compaction, other workloads), or CPU saturation.

## Mitigation

Rate-limit expensive routes at the proxy, move competing I/O away, or add replicas.

## Escalate when

Fast burn continues for 30 minutes after mitigation.

## Handoff

Use the [handoff note](README.md#handoff-note).
