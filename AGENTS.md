# AGENTS.md

Guidance for AI/automation agents (and humans) working in this repository.
Keep this file and `docs/current-state.md` (the supported-vs-experimental status
source of truth) up to date as the project changes.

## Project

- **Name:** Ghidra AI Exporter.
- **Purpose:** Turn an opened Ghidra program into a portable *evidence folder*
  that humans, scripts, and AI tools can query without keeping Ghidra open.
- **Evidence-first:** generated names, heuristics, and model output are **leads,
  never ground truth**. A conclusion is only trustworthy when concrete evidence
  (an import, string, xref, or accepted annotation) supports it.

## Stack

- **Host-side (normal Python 3):** the Flask HTTP API
  (`binary_agent_server.py`), the stdio MCP adapter
  (`binary_agent_mcp_server.py`), the read-only query core
  (`tools/local_evidence.py`), the CLI (`tools/evidence_tools.py`), and the
  derived-index / report / annotation tools under `tools/`.
- **Ghidra-side (Ghidra's own interpreter — Jython or PyGhidra, NOT host
  Python):** `run_exporter.py`, `AIExporter.py`, `pipeline.py`, `exporters/`,
  `util/`. These run inside Ghidra's Script Manager (or headless PyGhidra) and
  must not be imported by host tools or CI.
- **No C++ build in this repo.** The binaries being reverse-engineered are C++;
  they are the *target*, not code that lives or builds here.

## Commands

- Install (host-side): `pip install -r requirements.txt`
- Test (host-side only): `python -m unittest discover -s tests`
- Serve HTTP API: `python binary_agent_server.py --export <export> --port 5006`
- Validate an export: `python tools/validate_export.py <export> --full`
  (needs a real export folder — ask the maintainer for a path)

CI can run only the host-side unittest suite. Ghidra-side code cannot execute in
CI without a headless Ghidra install, so do not add CI steps that import
`exporters/`, `util/`, or the exporter entry points.

## Architecture invariants (do not break)

- **Raw is durable; derived is rebuildable.** Raw export files
  (`manifest.json`, `functions/<addr>.json`, `strings.json`, `imports.json`,
  `callgraph.json`, `index.json`, …) are the record of truth. Derived files
  (`local_evidence.sqlite3`, `class_registry.json`, `name_review_queue.json`)
  can be regenerated. Never make raw data depend on a derived file.
- **Annotations are a reversible overlay.** Accepted names live in
  `<export>/annotations/` and must stay deletable without changing raw Ghidra
  output. Nothing may write a name into the raw function JSON.
- **Keep the two environments separate.** `exporters/` and `util/` must never
  import host-only dependencies (`flask`, `requests`, `chromadb`,
  `sentence-transformers`, …) — they must stay runnable inside Ghidra.
- **The HTTP/MCP surfaces are local-only.** The Flask API binds to `127.0.0.1`;
  keep it local. The MCP adapter is stdio and read-mostly (its only writes are
  the reversible annotation overlay and the progress ledger — never raw export
  files or the Ghidra database).
- **Raw names (`FUN_...`) are identifiers, not conclusions.** Never present a
  generated or proposed name as confirmed behavior.

## Hard rules

- **Never push directly to `main`; never force-push `main`.** All changes go
  through pull requests. Do not merge a PR without the maintainer's review.
- **Branches:** `type/short-description` (e.g. `fix/search-crash`,
  `docs/api-drift`). **Commits:** Conventional Commits (`feat:`, `fix:`,
  `docs:`, `refactor:`, `chore:`).
- **Tests must pass locally** (`python -m unittest discover -s tests`) before
  opening or updating a PR. One logical change per PR; prefer small PRs.
- **Ask the maintainer before:** deleting files or branches; changing an export
  JSON format (`manifest.json`, `functions/*.json`, `callgraph.json`, etc.);
  changing public HTTP routes or MCP tool contracts; adding a dependency; or any
  destructive/irreversible action.
- **Never commit target artifacts:** binaries (`*.exe`, `*.dll`), export folders,
  `*.sqlite3`, archives of samples, or extracted copyrighted assets. If any are
  found in git history, stop and tell the maintainer immediately.
- **PR body:** what changed, why, and how it was tested.

## Where to look

- `docs/current-state.md` — supported vs experimental tools (status truth).
- `docs/getting-started.md`, `docs/architecture.md` — workflow and data contract.
- `docs/autonomous-agent.md` — running an MCP client (e.g. for unattended,
  resumable function naming) against an export.
