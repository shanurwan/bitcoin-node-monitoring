# ElectrsBitcoindRPCSlow

**Alerts:** `ElectrsBitcoindRPCSlow`  
**Severity:** warning

The 99th percentile latency of electrs's RPC calls to bitcoind, excluding `getblock`, has been above 2.5 s for 15 minutes.

## Impact

Slower indexing of new blocks and mempool sync, and slower REST/Electrum calls that go through to bitcoind.

## Triage

1. Dashboard: which methods are slow.
2. bitcoind CPU and disk; is bitcoind busy validating or flushing?
3. Network between electrs and bitcoind, if they run on different hosts.

## Likely causes

bitcoind under heavy load (IBD, reindex, a large mempool), slow disk, or a congested link.

## Mitigation

Reduce load on bitcoind or give it more resources.

## Escalate when

It is accompanied by ElectrsIndexBehind.

## Handoff

Use the [handoff note](README.md#handoff-note).
