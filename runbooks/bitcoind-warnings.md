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

## Handoff

Use the [handoff note](README.md#handoff-note).
