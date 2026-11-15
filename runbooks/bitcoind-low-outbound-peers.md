# BitcoindLowOutboundPeers

**Alerts:** `BitcoindLowOutboundPeers`  
**Severity:** warning

bitcoind has had fewer than 4 outbound connections for 30 minutes. Normal is 10 (8 full-relay, 2 block-relay-only).

## Impact

None yet, but the node hears about blocks later and is easier to isolate from the honest network.

## Triage

1. `bitcoin-cli getpeerinfo` – look at `inbound: false` peers and their `connection_type`.
2. `debug.log` for repeated connection failures, `-maxconnections` / `-onlynet` settings.

## Likely causes

- Restricted networking (`-onlynet=onion` with Tor trouble, a proxy that is down).
- `-maxconnections` set very low.
- Egress partially blocked.

## Mitigation

Fix the proxy or Tor service, or relax `-onlynet`. The node rebuilds outbound connections by itself once it can reach peers.

## Escalate when

It drops to zero (BitcoindNoPeers will page).

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindLowOutboundPeers on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
