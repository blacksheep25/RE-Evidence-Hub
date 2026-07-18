# Project exports

This is the default workspace for portable reverse-engineering evidence.
Every analysed program gets one self-contained directory:

```text
project_exports/
  TargetClient.exe/
    manifest.json
    index.json
    functions/
    annotations/
    agent_runs/
```

Project data is intentionally ignored by Git because exports can be large and
may contain sensitive target details. The directory structure and this guide
are tracked. Set `RE_EVIDENCE_PROJECTS_ROOT` to use another drive or shared
location without changing source code.

Unattended local-model output is isolated inside each project's
`agent_runs/<run-id>/` directory. See the
[overnight quick start](../docs/autonomous-agent.md) before starting, resuming,
reviewing, or discarding a pass.
