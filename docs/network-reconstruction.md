# Networking reconstruction

Networking recreation is an evidence-contract workflow, not a keyword search.

```powershell
revhub use TargetClient.exe
revhub network
```

This creates `derived/network/network_reconstruction.json` and `.md`. The pack
maps socket/Winsock/TLS imports to functions; groups setup, connect, send,
receive, multiplex, and shutdown stages; includes relationships; extracts
endpoint/protocol string leads; and lists unresolved contracts.

MCP agents can call `binary_network_map` for the same report without writing
the derived files. Use a bounded `limit` and investigate one stage at a time.

## Confidence boundaries

- Import references prove a static API reference.
- Strings prove static presence, not runtime behavior.
- Only accepted annotations are active semantic names.
- The report does not infer packet fields, byte order, crypto, opcode meaning,
  reconnect policy, or server behavior.

## Recreation workflow

1. Build the pack and select one lifecycle stage.
2. Inspect each function with `revhub query lookup <address>`.
3. Follow relevant callers/callees until buffers and state transitions are
   explicit; verify critical decompiler claims against assembly/xrefs.
4. When authorised, correlate runtime traffic/logs with static send/receive
   paths and record capture provenance/version.
5. Write a reviewed protocol contract containing only confirmed framing,
   direction, state prerequisites, offsets/types, and failure behavior.
6. Implement against that contract with encode/decode fixtures and negative
   tests for malformed, truncated, oversized, out-of-order messages.

Keep transport, framing, serialization, crypto/compression, dispatch, and
session state separate so uncertainty in one layer does not contaminate others.
