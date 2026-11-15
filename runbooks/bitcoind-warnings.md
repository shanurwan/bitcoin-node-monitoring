# BitcoindWarnings

**Alerts:** `BitcoindWarnings`  
**Severity:** warning

`getblockchaininfo` has returned warnings for 15 minutes.

## Impact

Depends on the warning. Some are cosmetic (a pre-release build); some mean the node may be following rules the network has moved past.

## Triage

1. `bitcoin-cli getblockchaininfo` and read `warnings`.
2. `bitcoin-cli getnetworkinfo` also has a `warnings` field.

## Likely causes

- "Unknown new rules activated": the network activated a soft fork this version does not know. Upgrade soon.
- Clock out of sync with peers: fix NTP on the host.
- Running a release candidate or a development build.

## Mitigation

Upgrade for unknown rules, fix time sync, or accept the warning for test builds (then silence this alert for that node).

## Escalate when

Unknown new rules: plan an upgrade with the owners of the service.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindWarnings on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
