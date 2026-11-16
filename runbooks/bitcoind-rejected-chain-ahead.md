# BitcoindRejectedChainAhead

**Alerts:** `BitcoindRejectedChainAhead`  
**Severity:** critical

bitcoind has marked a block invalid that is higher than its own tip, for 10 minutes. Some peers are
building on a chain this node refuses. One of two things is true:

- **This node is wrong.** It rejects blocks the rest of the network accepts. In March 2013 a database
  lock limit made Bitcoin 0.7 nodes reject a large block that 0.8 nodes accepted, and the network split
  for about six hours ([BIP 50](https://github.com/bitcoin/bips/blob/master/bip-0050.mediawiki)).
- **Part of the network is wrong.** Miners extend an invalid chain. In July 2015 miners that did not
  validate blocks built six blocks on an invalid one after the BIP 66 soft fork activated.

bitcoind drops headers that build on an invalid block, so `headers` does not move ahead of `blocks` and
`BitcoindBlocksBehindHeaders` stays quiet. On one node this alert is the only fast signal.

## Impact

If this node is wrong, electrs serves a chain the network has left: balances and confirmations are wrong,
and deposits credited from it can be reversed. If the network is split, every service that trusts
confirmations is at risk until it resolves.

## Triage

1. `bitcoin-cli getchaintips` – find the `invalid` tip above the `active` one. Note its hash and height.
2. `bitcoin-cli getblockheader <hash>` and `grep -i "invalid\|ConnectBlock" debug.log` – the reject reason.
3. Compare with other nodes: your other bitcoind nodes (`BitcoindBehindFleet` fires if this one is behind
   them), a different implementation or version, and public explorers. Who has the higher tip?
4. Check the Bitcoin Core announcements and the bitcoin-dev list for a known issue.

## Likely causes

- A consensus bug or a resource limit in this node's version (the 2013 case).
- Miners building on an invalid block (the 2015 case). Your node is right; wait it out.
- Someone ran `bitcoin-cli invalidateblock` by hand.

## Mitigation

- **Stop trusting confirmations first.** Raise the confirmation count for deposits, or pause them,
  until you know which chain wins.
- If this node is the odd one out and others accept the block: upgrade or downgrade to the version the
  network follows, or `reconsiderblock <hash>` once the cause is understood.
- If a manual `invalidateblock` is the cause: `bitcoin-cli reconsiderblock <hash>`.
- If miners are building an invalid chain: keep running; your node is following the valid chain.

## Escalate when

Immediately. A chain split needs the incident lead and whoever decides on pausing deposits and withdrawals.

## Handoff

Use the [handoff note](README.md#handoff-note).
