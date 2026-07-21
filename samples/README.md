# Sample export

`tiny_export/` is a hand-authored, 2-function export. It lets you try every
host-side workflow **without Ghidra, Java, or a target binary** — useful for a
first look, for demos, and as the fixture the CI smoke test runs against.

It is deliberately tiny and is **not** produced by Ghidra; it just conforms to
the same on-disk contract a real export does (`manifest.json`, `index.json`,
`functions/`, `strings.json`, `imports.json`, `globals.json`, `callgraph.json`,
and an accepted-annotation overlay under `annotations/`).

## Try it in 30 seconds

Install the baseline (`pip install flask requests numpy`), then:

```powershell
# Validate the structure
python .\tools\validate_export.py samples\tiny_export --full

# One-off query, no server needed
python .\tools\evidence_tools.py --export samples\tiny_export status
python .\tools\evidence_tools.py --export samples\tiny_export lookup CExampleUi_ApplyLayout --no-decompiler

# Or serve the HTTP API and query it
python .\binary_agent_server.py --export samples\tiny_export
# then, in another shell:
#   Invoke-RestMethod http://127.0.0.1:5006/status
```

The `lookup` shows the annotation overlay in action: the raw Ghidra name is
`FUN_00401000`, and the accepted, evidence-backed name `CExampleUi_ApplyLayout`
appears as `active_name`.

## What it demonstrates

- **Accepted annotation overlay** — `00401000` carries an accepted name with
  evidence, so `active_name` overlays `raw_name`.
- **Derived indexes** — `build_local_index.py`, `build_class_registry.py`, and
  `build_name_review_queue.py` all run against it (the `.?AVCExampleUi@@` RTTI
  string and the `send` import feed the class registry and review queue).
- **Relationships and evidence** — `00401000` calls `00402000`, references the
  `login_panel.asset` string, and `00402000` references the `send` import.

Derived files written beside the sample (`local_evidence.sqlite3`,
`class_registry.json`, `name_review_queue.json`) are gitignored, so running the
demo will not dirty the working tree.
