# Reversible function-name annotations

Use `tools/function_annotations.py` to record names inferred during reverse
engineering. It writes only to `<export>/annotations/`, never modifies the raw
function export, search index, or Ghidra symbol table. Deleting that folder
removes the entire naming pass.

Each decision is keyed by the exported function address and records the current
assembly hash and range. The validator reports a warning if a future export has
different code at the same address.

## Workflow

```powershell
python .\tools\function_annotations.py init <export-folder>
python .\tools\function_annotations.py set <export-folder> 0047c8d0 Net_UdpSendAck --confidence high --evidence "Calls sendto with literal ACK payload" --evidence "Direct caller logs failed to send ack"
python .\tools\function_annotations.py validate <export-folder>
python .\tools\function_annotations.py list <export-folder>
```

`function_names.json` is authoritative. `function_names.md` is a regenerated,
compact review view. A name may have a `proposed`, `accepted`, `superseded`, or
`rejected` status; only an accepted decision becomes the entry's `active_name`.

## Naming convention

- Use `PascalCase`, normally `Subsystem_VerbObjectQualifier`.
- Keep the subsystem broad unless a class or game feature is directly proven.
- Use `high` confidence only with direct assembly/API/string/data evidence.
- Preserve competing or earlier names as decisions instead of overwriting them.
- Treat all names as annotations. Apply them to Ghidra only after a separately
  reviewed naming pass.

This works with any valid export folder; its target identity is read from that
export's `manifest.json`, not hard-coded to target.
