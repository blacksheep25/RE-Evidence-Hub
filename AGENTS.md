# Project

- **Name:** Ghidra AI Exporter.
- **Purpose:** Turn an opened Ghidra program into a portable evidence folder that
  humans, scripts, and AI tools can query without keeping Ghidra open.
- **Evidence-first:** Generated names, heuristics, and model output are leads,
  never ground truth. Confirm behaviour from concrete exported evidence.

# Stack

- **Host-side Python 3:** `binary_agent_server.py`,
  `binary_agent_mcp_server.py`, `tools/local_evidence.py`,
  `tools/evidence_tools.py`, and host tools under `tools/` and `ai_tools/`.
- **Ghidra-side:** `run_exporter.py`, `AIExporter.py`, `pipeline.py`,
  `exporters/`, and `util/` run in Ghidra's Python environment, not ordinary
  host Python. The verified Ghidra 12.x workflow launches the UI through
  PyGhidra; follow `docs/getting-started.md` for the current launch path.
- **There is no C++ build in this repository.** C++ binaries are reversing
  targets and must not be committed.

# Commands

- Install: `pip install -r requirements.txt`
- Test host-side code: `python -m unittest discover -s tests`
- Serve: `python binary_agent_server.py --export <export> --port 5006`
- Validate an export: `python tools/validate_export.py <export> --full`
  (requires a real or synthetic export folder)

CI covers host-side Python only. Do not import the Ghidra-side entry points,
`exporters/`, or `util/` from host-only CI tests.

# Architecture invariants

- Raw export files are the durable record. Derived files such as
  `local_evidence.sqlite3`, `class_registry.json`, and
  `name_review_queue.json` must remain rebuildable from raw evidence.
- Accepted annotations live in `<export>/annotations/` as a reversible overlay.
  Deleting the overlay must never change raw Ghidra output.
- `exporters/` and `util/` must not import host-only dependencies such as Flask,
  Requests, Chroma, or sentence-transformers.
- The HTTP API binds to `127.0.0.1` and must remain local-only. The MCP adapter
  uses local stdio. Any write-capable tool must be explicitly reviewed and may
  write only reversible annotations or derived progress state, never raw export
  files or the Ghidra database.
- Raw names such as `FUN_...` are identifiers, not conclusions. Never present a
  generated or proposed name as confirmed behaviour.

# Hard rules

- Never push directly to `main` or force-push `main`; use pull requests.
- Name branches `type/short-description` and use Conventional Commit messages
  (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- Run `python -m unittest discover -s tests` before opening or updating a PR.
  Keep each PR to one logical concern.
- Ask the maintainer before deleting files or branches, changing export JSON
  formats, changing public HTTP routes or MCP tool contracts, adding a
  dependency, or taking a destructive or irreversible action.
- Never commit target binaries (`*.exe`, `*.dll`, `*.bin`), export folders,
  databases (`*.sqlite`, `*.sqlite3`), archives of samples, or extracted
  copyrighted assets. If any are found in history, stop and notify the
  maintainer.
- PR descriptions must explain what changed, why, and how it was tested.
- Keep this file and `docs/current-state.md` aligned as the project changes.

# Where to look

- `README.md` and `docs/getting-started.md` for onboarding.
- `docs/current-state.md` for supported versus experimental status.
- `docs/architecture.md` for runtime boundaries and data contracts.

