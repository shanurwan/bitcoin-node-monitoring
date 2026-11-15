# BitcoindNoPeers

**Alerts:** `BitcoindNoPeers`  
**Severity:** critical

bitcoind has had zero P2P connections for 10 minutes.

## Impact

The node does not receive new blocks or transactions, so electrs serves an increasingly stale chain and mempool.

## Triage

1. `bitcoin-cli getnetworkinfo` – check `networkactive` and `connections`.
2. `bitcoin-cli getpeerinfo | grep -c addr` and the end of `debug.log` for connection errors.
3. From the host: can it reach the internet on the P2P port (8333 mainnet, 48333 testnet4)? Check firewalls, NetworkPolicies, egress NAT and DNS seeds.

## Likely causes

- Networking turned off (`setnetworkactive false`, or `-connect=` pointing at a dead peer).
- Egress blocked by a firewall or Kubernetes NetworkPolicy change.
- The host lost its network or DNS.

## Mitigation

- `bitcoin-cli setnetworkactive true` if it was turned off.
- Revert the firewall or policy change.
- As a stopgap, `bitcoin-cli addnode <known-good-peer> onetry`.

## Escalate when

No peers after the network path is confirmed open, or several nodes lose peers at once (a provider or regional issue).

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindNoPeers on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
