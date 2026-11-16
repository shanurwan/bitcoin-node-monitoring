# BitcoindNoNewBlocks

**Alerts:** `BitcoindNoNewBlocks` (warning), `BitcoindBehindFleet` (critical)  
**Severity:** warning / critical

`BitcoindNoNewBlocks`: bitcoind's height has not changed for 95 minutes and the node is not in initial block
download. `BitcoindBehindFleet`: the node has been more than 2 blocks behind your highest node for 10 minutes (needs
two or more nodes).

`BitcoindNoNewBlocks` is a warning because a real 95-minute gap between mainnet blocks happens about four times a
year, on every node at once. A node that is stuck while the others move on is what `BitcoindBehindFleet` pages for.

## Impact

If the node is stuck, every client of electrs sees stale confirmations and balances.

## Triage

1. Compare with an independent source (another node you run, or a public explorer): is there really no new block?
2. `bitcoin-cli getblockchaininfo` – `headers` greater than `blocks` means the node knows about blocks it has not validated (see [BitcoindBlocksBehindHeaders](bitcoind-blocks-behind-headers.md)).
3. `bitcoin-cli getpeerinfo` – does it have peers, and do their `synced_blocks` / `synced_headers` exceed your height?
4. `bitcoin-cli getchaintips` – an `invalid` tip at the network's height means your node rejected a block.

## Likely causes

- The network is slow: the chance of no mainnet block for 95 minutes is e^-9.5, about 1 in 13,000 block intervals,
  or about four times a year. Testnets can be irregular. If every node alerts at once, this is the likely cause.
- The node is partitioned (few or no peers, or only peers that are themselves stuck).
- The node rejected a block, for example after a consensus-rule change it does not know about (bitcoind also reports a warning).

## Mitigation

- Real network gap: nothing to do; resolve once a block arrives.
- Partitioned: fix peers (see [bitcoind-no-peers](bitcoind-no-peers.md)) or `addnode` a known-good peer.
- Rejected block: do not `reconsiderblock` blindly. Find out why (`debug.log`), and check whether an upgrade is needed.

## Escalate when

Other nodes have moved on and yours has not, or `getchaintips` shows an invalid tip.

## Handoff

Use the [handoff note](README.md#handoff-note).
