# BitcoindDown

**Alerts:** `BitcoindDown`  
**Severity:** critical

The exporter cannot get an answer from bitcoind's JSON-RPC, or Prometheus cannot scrape the exporter.

## Impact

electrs stops indexing new blocks and cannot broadcast transactions. Anything else using this bitcoind's RPC fails.

## Triage

1. Find out which half failed. In Prometheus: `up{job="bitcoind"}` is 0 when the exporter is down; `bitcoind_up` is 0 when the exporter runs but RPC fails.
2. Is bitcoind running? `systemctl status bitcoind` / `kubectl get pod -l app=bitcoind`, and the tail of `debug.log`.
3. Can you reach RPC yourself? `bitcoin-cli getblockchaininfo`. A hang usually means bitcoind is busy (startup, reindex, `-rpcworkqueue` full); an auth error means the cookie or password changed.
4. Exporter logs print the RPC error on every failed scrape.

## Likely causes

- bitcoind is starting: loading the block index and verifying recent blocks takes minutes on mainnet, and RPC answers `Loading block index` (error -28) until it finishes.
- bitcoind crashed or was OOM-killed (`dmesg`, `journalctl -k`), or stopped because the disk is full.
- The `.cookie` file was rewritten on restart and the exporter still sends the old one (the exporter re-reads `BITCOIND_RPC_COOKIE` on every scrape; user/password setups need updating by hand).
- RPC work queue full: `debug.log` shows `WARNING: request rejected because http work queue depth exceeded`.

## Mitigation

- Starting: wait, and watch `debug.log` progress. Do not restart it again; that starts the wait over.
- Crashed: restart it and check for corruption messages before letting electrs reconnect.
- Disk full: free space first (see [bitcoin-node-disk](bitcoin-node-disk.md)); bitcoind refuses to start with too little space.
- Work queue: raise `-rpcworkqueue` / `-rpcthreads`, or find the client flooding RPC.

## Escalate when

bitcoind does not come back within 30 minutes, or `debug.log` reports database corruption (a reindex takes hours on mainnet and needs a decision).

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      BitcoindDown on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
