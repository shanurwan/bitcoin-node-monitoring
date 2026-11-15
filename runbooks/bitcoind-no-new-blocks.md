# BitcoindNoNewBlocks

**Alerts:** `BitcoindNoNewBlocks`  
**Severity:** critical

bitcoind's height has not changed for 95 minutes and the node is not in initial block download.

## Impact

If the node is stuck, every client of electrs sees stale confirmations and balances.

## Triage

1. Compare with an independent source (another node you run, or a public explorer): is there really no new block?
2. `bitcoin-cli getblockchaininfo` – `headers` greater than `blocks` means the node knows about blocks it has not validated (see [BitcoindBlocksBehindHeaders](bitcoind-blocks-behind-headers.md)).
3. `bitcoin-cli getpeerinfo` – does it have peers, and do their `synced_blocks` / `synced_headers` exceed your height?
4. `bitcoin-cli getchaintips` – an `invalid` tip at the network's height means your node rejected a block.

## Likely causes

- The network is slow: on mainnet a 95-minute gap happens roughly once in 8,000 such windows, so occasionally it is real. Testnets can be irregular.
- The node is partitioned (few or no peers, or only peers that are themselves stuck).
- The node rejected a block, for example after a consensus-rule change it does not know about (bitcoind also reports a warning).

## Mitigation

- Real network gap: nothing to do; resolve once a block arrives.
- Partitioned: fix peers (see [bitcoind-no-peers](bitcoind-no-peers.md)) or `addnode` a known-good peer.
- Rejected block: do not `reconsiderblock` blindly. Find out why (`debug.log`), and check whether an upgrade is needed.

## Escalate when

Other nodes have moved on and yours has not, or `getchaintips` shows an invalid tip.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindNoNewBlocks on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
