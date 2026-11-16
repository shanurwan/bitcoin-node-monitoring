# Runbooks

One runbook per alert, or per pair of closely related alerts. Each has the alert's meaning, impact, triage commands,
likely causes, mitigation, and when to escalate.

| Runbook | Alerts |
|---|---|
| [bitcoin-node-disk](bitcoin-node-disk.md) | `BitcoinNodeDiskWillFill`, `BitcoinNodeDiskAlmostFull`, `BitcoinNodeVolumeWillFill`, `BitcoinNodeVolumeAlmostFull` |
| [bitcoind-blocks-behind-headers](bitcoind-blocks-behind-headers.md) | `BitcoindBlocksBehindHeaders` |
| [bitcoind-down](bitcoind-down.md) | `BitcoindDown`, `BitcoindWarmupTooLong` |
| [bitcoind-initial-block-download-stalled](bitcoind-initial-block-download-stalled.md) | `BitcoindInitialBlockDownloadStalled` |
| [bitcoind-low-outbound-peers](bitcoind-low-outbound-peers.md) | `BitcoindLowOutboundPeers` |
| [bitcoind-no-new-blocks](bitcoind-no-new-blocks.md) | `BitcoindNoNewBlocks`, `BitcoindBehindFleet` |
| [bitcoind-no-peers](bitcoind-no-peers.md) | `BitcoindNoPeers` |
| [bitcoind-rejected-chain-ahead](bitcoind-rejected-chain-ahead.md) | `BitcoindRejectedChainAhead` |
| [bitcoind-restart-loop](bitcoind-restart-loop.md) | `BitcoindRestartLoop` |
| [bitcoind-warnings](bitcoind-warnings.md) | `BitcoindWarnings` |
| [electrs-bitcoind-rpc-errors](electrs-bitcoind-rpc-errors.md) | `ElectrsBitcoindRPCErrors` |
| [electrs-bitcoind-rpc-slow](electrs-bitcoind-rpc-slow.md) | `ElectrsBitcoindRPCSlow` |
| [electrs-down](electrs-down.md) | `ElectrsDown` |
| [electrs-electrum-fd-limit](electrs-electrum-fd-limit.md) | `ElectrsElectrumFdLimit` |
| [electrs-electrum-latency-slo](electrs-electrum-latency-slo.md) | `ElectrsElectrumLatencyBurnFast`, `ElectrsElectrumLatencyBurnSlow` |
| [electrs-index-behind](electrs-index-behind.md) | `ElectrsIndexBehind` |
| [electrs-initial-sync-stalled](electrs-initial-sync-stalled.md) | `ElectrsInitialSyncStalled` |
| [electrs-main-loop-stalled](electrs-main-loop-stalled.md) | `ElectrsMainLoopStalled` |
| [electrs-memory-high](electrs-memory-high.md) | `ElectrsMemoryHigh`, `ElectrsContainerMemoryHigh`, `BitcoinNodeOOMKilled` |
| [electrs-mempool-sync-failing](electrs-mempool-sync-failing.md) | `ElectrsMempoolSyncFailing` |
| [electrs-rest-availability-slo](electrs-rest-availability-slo.md) | `ElectrsRESTAvailabilityBurnFast`, `ElectrsRESTAvailabilityBurnSlow` |
| [electrs-rest-latency-slo](electrs-rest-latency-slo.md) | `ElectrsRESTLatencyBurnFast`, `ElectrsRESTLatencyBurnSlow` |
| [electrs-restart-loop](electrs-restart-loop.md) | `ElectrsRestartLoop` |
| [electrs-rocksdb-background-errors](electrs-rocksdb-background-errors.md) | `ElectrsRocksDBBackgroundErrors` |
| [electrs-rocksdb-write-stopped](electrs-rocksdb-write-stopped.md) | `ElectrsRocksDBWriteStopped`, `ElectrsRocksDBWriteDelayed` |
| [electrs-stale-cleanup-failing](electrs-stale-cleanup-failing.md) | `ElectrsStaleCleanupFailing` |

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      <alert name> on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
