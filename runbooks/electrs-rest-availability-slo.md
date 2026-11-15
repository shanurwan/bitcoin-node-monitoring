# ElectrsRESTAvailabilityBurnFast / ElectrsRESTAvailabilityBurnSlow

**Alerts:** `ElectrsRESTAvailabilityBurnFast`, `ElectrsRESTAvailabilityBurnSlow`  
**Severity:** critical (fast) / warning (slow)

More REST requests are returning 5xx than the 99.5% availability objective allows, fast enough to use up the 30-day error budget early.

## Impact

Clients of the Esplora-style REST API (explorers, wallets) get server errors.

## Triage

1. Which window fired? Fast burn (critical) means the budget would be gone within days; slow burn (warning) within weeks.
2. Dashboard "electrs serving" row: which routes or methods produce the bad requests, and since when.
3. Correlate with deploys, ElectrsIndexBehind, RPC alerts and host load.
4. `rest_request_duration_seconds_count` by `route` and `status`: one route or all of them?

## Likely causes

bitcoind RPC failures surfacing as 5xx, electrs overloaded, or a bad release.

## Mitigation

Roll back a recent change, shed load at the proxy, or fix the RPC dependency. The objective is set in `scripts/generate.py`; change it there if it does not match what you promise users.

## Escalate when

Fast burn continues for 30 minutes after mitigation.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsRESTAvailabilityBurnFast on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
