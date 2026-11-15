# BitcoindInitialBlockDownloadStalled

**Alerts:** `BitcoindInitialBlockDownloadStalled`  
**Severity:** warning

bitcoind is in initial block download and its height has not changed for 45 minutes.

## Impact

A new node is not getting closer to usable. electrs cannot start indexing until bitcoind is synced.

## Triage

1. `bitcoin-cli getblockchaininfo` – `blocks`, `headers`, `verificationprogress`.
2. `debug.log` – is it flushing the chainstate (can take many minutes with a large `-dbcache`), or logging errors?
3. Peers (`getpeerinfo`) and disk space.

## Likely causes

- A long chainstate flush, which looks like a stall but is not.
- No peers, or the disk filled up.
- `-assumevalid`/`-dbcache` choices making validation very slow on small hardware.

## Mitigation

Free disk, fix peers, and give the flush time to finish. Running IBD on a fast local disk with a generous `-dbcache` is much quicker than on network storage.

## Escalate when

No progress for 2 hours with peers and disk confirmed healthy.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindInitialBlockDownloadStalled on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
