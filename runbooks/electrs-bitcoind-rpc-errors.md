# ElectrsBitcoindRPCErrors

**Alerts:** `ElectrsBitcoindRPCErrors`  
**Severity:** warning

electrs's new RPC connections to bitcoind fail their handshake more than 3 times in 15 minutes, or more than 10
proxied client calls in 15 minutes find no free slot or get no answer. The alert is suppressed while `bitcoind_up` is
0, since then `BitcoindDown` covers it.

What the results mean, from electrs's source:

| Metric | `result` | Meaning |
|---|---|---|
| `daemon_rpc_conn_handshake` | `rejected` | bitcoind answered, but not with a JSON-RPC reply: 401 (wrong cookie or password), 403 (`-rpcwhitelist`), or a malformed response |
| | `timeout` | the connection was accepted but the handshake got no answer in time: bitcoind overloaded or at `-rpcmaxconnections` |
| | `error` | connecting failed (refused, reset) |
| `daemon_rpc_proxied` | `busy` | every client RPC slot was in use and the call gave up waiting |
| | `unavailable` | the call to bitcoind failed or timed out at the transport level |
| | `error` | bitcoind answered with an RPC error, such as rejecting a client's transaction. Normal on a public instance, so the alert ignores it |

## Impact

Slower or failing block and transaction fetches; broadcasts through electrs may fail.

## Triage

1. Dashboard: handshake results and proxied call results.
2. bitcoind `debug.log` for `rejected because http work queue depth exceeded`, and `bitcoin-cli getrpcinfo`.
3. Compare electrs's `--daemon-parallelism` with bitcoind's `-rpcthreads`, `-rpcworkqueue` and
   `-rpcmaxconnections`.

## Likely causes

- bitcoind at its RPC limits (`-rpcmaxconnections`, `-rpcthreads`, `-rpcworkqueue`): connections are accepted but
  not served, which electrs counts as `timeout`.
- Credentials: a rewritten `.cookie` or a `-rpcwhitelist` that does not include a method electrs calls (`rejected`).
- bitcoind restarting.
- Other heavy RPC clients on the same bitcoind.

## Mitigation

Raise bitcoind's `-rpcthreads`, `-rpcworkqueue` or `-rpcmaxconnections`, lower electrs's `--daemon-parallelism`,
or move other clients off this bitcoind. For `rejected`, fix the credentials or the whitelist.

## Escalate when

Errors continue after the limits are raised.

## Handoff

Use the [handoff note](README.md#handoff-note).
