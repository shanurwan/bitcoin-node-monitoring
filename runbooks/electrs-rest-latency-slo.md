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

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsRESTLatencyBurnFast on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
