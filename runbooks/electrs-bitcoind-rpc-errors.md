# ElectrsBitcoindRPCErrors

**Alerts:** `ElectrsBitcoindRPCErrors`  
**Severity:** warning

electrs's new RPC connections to bitcoind are being rejected or timing out, or proxied RPC calls are failing.

## Impact

Slower or failing block and transaction fetches; broadcasts through electrs may fail.

## Triage

1. Dashboard: handshake results and proxied call results.
2. bitcoind `debug.log` for `rejected because http work queue depth exceeded`, and `bitcoin-cli getrpcinfo`.
3. Compare electrs's RPC thread count with bitcoind's `-rpcthreads` and `-rpcworkqueue`.

## Likely causes

- bitcoind at its RPC connection or work-queue limits (`-rpcthreads`, `-rpcworkqueue`). electrs detects connections that are accepted but never served at the cap and reports them as rejected.
- bitcoind restarting.
- Other heavy RPC clients on the same bitcoind.

## Mitigation

Raise bitcoind's `-rpcthreads`/`-rpcworkqueue`, lower electrs's RPC parallelism, or move other clients off this bitcoind.

## Escalate when

Errors continue after the limits are raised.

## Handoff note

Copy this into the incident channel or ticket when you hand over:

```text
Alert:      ElectrsBitcoindRPCErrors on <node>, firing since <UTC time>
Impact:     <who is affected and how; "none yet" is a valid answer>
Checked:    <what you looked at and what it showed>
Done:       <actions taken, with times>
State now:  <current heights / error rates / memory, from the dashboard>
Next:       <what the next person should do or watch, and when to escalate>
```
