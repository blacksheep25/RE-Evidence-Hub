# Projects and exports

## Layout

Every program gets one portable directory:

```text
project_exports/Client.exe/
  manifest.json, index.json, functions/   raw evidence
  annotations/                            accepted reversible conclusions
  derived/network/                        rebuildable networking report
  agent_runs/night-01/                    disposable model pass
```

Project contents are Git-ignored. Never commit binaries, proprietary exports,
derived databases, or agent runs.

```powershell
revhub projects
revhub use Client.exe
revhub query status
```

`revhub use` also accepts a path. Its pointer contains no evidence; it only
selects a folder.

## Relocate the root

```powershell
$env:RE_EVIDENCE_PROJECTS_ROOT = 'X:\RE-Evidence-Projects'
```

The GUI exporter, headless exporter, project discovery, and host defaults use
this variable. Restart Ghidra/services after changing it. Explicit paths and
`GHIDRA_AI_EXPORT_PATH` stay compatible.

## Backup and deletion

- Back up raw JSON and accepted `annotations/` together.
- Derived files and `agent_runs/` can be omitted.
- Validate restored data with `revhub validate --full`.
- This repository intentionally provides no destructive project-delete command.
