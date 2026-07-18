# AI agent guide

Use the hub to retrieve bounded evidence and produce reviewable conclusions.
Search ranking, decompiler prose, raw `FUN_` names, and model familiarity are
not facts.

## Session start

1. Read `AGENTS.md`, this guide, and the subsystem document.
2. Run `revhub doctor` and `revhub query status`.
3. Confirm binary, image base/language, function count, and export path.
4. Validate the export when integrity is unknown.

## Retrieval discipline

- Search for an exact API, string, address, control id, opcode lead, or name.
- Use `lookup`, then follow only relevant callers/callees.
- Preserve addresses and distinguish raw, accepted, and proposed names.
- Check assembly/xrefs for critical branches, sizes, and data flow.
- State confidence, unknowns, and the next verification action.
- Never dump the whole export into context.

## Writes and handoff

Raw evidence is immutable. Reviewed conclusions may enter `annotations/`.
Unattended models write only to `agent_runs/<run-id>/` via
`binary_propose_name`; a separate reviewer accepts/rejects them.

Findings should include address, name status, concrete strings/imports and
relationships, control-flow explanation, confidence, unresolved questions,
and exact next check. Networking work follows
[Networking reconstruction](network-reconstruction.md).
