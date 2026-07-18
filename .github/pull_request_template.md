<!--
Repo conventions: see AGENTS.md. Conventional-commit style title (feat:, fix:,
docs:, refactor:, chore:). One logical change per PR; prefer small PRs.
-->

## What changed

<!-- A short summary of the change. -->

## Why

<!-- The problem or motivation. Link any issue. -->

## How tested

<!-- e.g. `python -m unittest discover -s tests` (all pass); export validated
     with `python tools/validate_export.py <export> --full`; manual steps. -->

## Checklist

- [ ] Host-side tests pass locally: `python -m unittest discover -s tests`
- [ ] One logical change; PR title is Conventional-Commit style
- [ ] `exporters/` and `util/` still import no host-only deps (stay Ghidra-runnable)
- [ ] No target artifacts committed (`*.exe`/`*.dll`/`*.bin`, export folders, `*.sqlite3`, copyrighted assets)
- [ ] Raw data does not depend on derived files; annotations stay a reversible overlay
- [ ] Maintainer sign-off obtained before any: export-JSON format change, HTTP route / MCP tool contract change, new dependency, or destructive/irreversible action
- [ ] Docs updated if behavior changed (`docs/current-state.md`, relevant `docs/`)
