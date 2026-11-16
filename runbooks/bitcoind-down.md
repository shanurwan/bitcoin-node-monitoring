# BitcoindDown

**Alerts:** `BitcoindDown`, `BitcoindWarmupTooLong`  
**Severity:** critical

`BitcoindDown`: the exporter cannot get an answer from bitcoind's JSON-RPC, Prometheus cannot scrape the exporter,
or there is no exporter target at all (for one node, or for every node). `BitcoindWarmupTooLong`: bitcoind answers,
but only with "in warmup" (error -28), and has done so for 30 minutes.

## Impact

electrs stops indexing new blocks and cannot broadcast transactions. Anything else using this bitcoind's RPC fails.

## Triage

1. Find out which part failed. In Prometheus: no `up{job="bitcoind"}` series for the node means the exporter is not
   scheduled or not discovered (`kubectl get pod`, check the pod is not Pending, check the ServiceMonitor selector and
   the `bitcoin-node` pod label); `up` is 0 when the exporter is down; `bitcoind_up` is 0 when the exporter runs but
   RPC fails, and `bitcoind_rpc_warmup` is 1 when bitcoind is still starting.
   A scrape job removed from the Prometheus config pages late: in the game day, Prometheus 3.15.1 kept serving the
   job's last sample for 5 minutes after the reload, so the page came about 10 minutes after the change, not 5. If
   a config change went out in the last 15 minutes, check it first.
2. Is bitcoind running? `systemctl status bitcoind` / `kubectl get pod -l app=bitcoind`, and the tail of `debug.log`.
3. Can you reach RPC yourself? `bitcoin-cli getblockchaininfo`. A hang usually means bitcoind is busy (startup, reindex, `-rpcworkqueue` full); an auth error means the cookie or password changed.
4. Exporter logs print the RPC error on every failed scrape.

## Likely causes

- The pod is not running at all: Pending (no node with the zone of its persistent disk, or no capacity), or the
  StatefulSet was scaled to 0.
- bitcoind crashed or was OOM-killed (`dmesg`, `journalctl -k`), or stopped because the disk is full.
- The `.cookie` file was rewritten on restart and the exporter still sends the old one (the exporter re-reads `BITCOIND_RPC_COOKIE` on every scrape; user/password setups need updating by hand).
- RPC work queue full: `debug.log` shows `WARNING: request rejected because http work queue depth exceeded`.

## Mitigation

- Crashed: restart it and check for corruption messages before letting electrs reconnect.
- Disk full: free space first (see [bitcoin-node-disk](bitcoin-node-disk.md)); bitcoind refuses to start with too little space.
- Work queue: raise `-rpcworkqueue` / `-rpcthreads`, or find the client flooding RPC.

## Still warming up

`BitcoindWarmupTooLong` fires after 30 minutes of error -28. `BitcoindDown` stays quiet during warmup, so a normal
restart does not page.

- `debug.log` shows the phase: `Loading block index`, `Verifying last N blocks`, or `Replaying blocks` /
  `Rolling forward` after an unclean shutdown. Replaying can take a long time if a large `-dbcache` was not flushed.
- Watch it progress rather than restarting: a restart starts the wait over, and killing it during a replay makes the
  next start replay again.
- `bitcoin-cli getblockchaininfo` keeps returning error -28 until it finishes; electrs waits and retries meanwhile,
  which is why `ElectrsMainLoopStalled` is suppressed while `bitcoind_up` is 0.
- A warmup that does not progress for an hour, or `debug.log` reporting corruption, needs a decision about
  `-reindex-chainstate` or `-reindex`, which take hours on mainnet.

## Escalate when

bitcoind does not come back within 30 minutes, or `debug.log` reports database corruption (a reindex takes hours on mainnet and needs a decision).

## Handoff

Use the [handoff note](README.md#handoff-note).
