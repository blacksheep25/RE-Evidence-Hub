# Experimental / unsupported

This directory holds host-side code that is **not part of the supported evidence
workflow**: semantic/vector search, embeddings, LLM/agent helpers, and older
duplicate implementations. It is kept for reference and iteration, not for
day-to-day use.

Treat everything here as **leads only** — the project is evidence-first, and
these tools produce model guesses, semantic hints, or automation output that are
not ground truth. For the supported workflow (export → query → annotate), use
the root scripts and `tools/` as described in the main
[README](../README.md) and [Getting started](../docs/getting-started.md).

## What is here

| Path | Role |
| --- | --- |
| `ai_tools/` | Older vector, Chroma, graph, and semantic-search helpers. |
| `hybrid.py`-style search, `vector_query.py`, `llm_interface.py` | Semantic/vector/LLM query surfaces (need optional deps). |
| `reverse_engineering_agent.py` | LLM-driven agent experiment. |
| `build_index.py`, `build_embeddings_host.py` | Chroma/embedding index builders. |
| `function_ghidra_binary_analyst.py` | Prompt template for an Open WebUI/Ollama-style integration. |
| `legacy_tests/` | Old ad-hoc test scripts (not the maintained suite under `tests/`). |

The maintained tests live in the top-level [`tests/`](../tests) directory and
run with `python -m unittest discover -s tests`. Nothing here is exercised by
that suite or by CI.

## Caveats

- **Requirements:** these modules need the optional stack (`chromadb`,
  `sentence-transformers`, and in some cases an LLM API). Install it with the
  project's optional extras before expecting any of this to run.
- **Not repaired, only relocated:** files were moved here as-is. Some retain
  fragile imports and assume they are run with the repository root (and, for a
  few `ai_tools/` modules, their own directory) on `PYTHONPATH`. In particular,
  `ai_tools/build_embeddings.py` references config names its sibling
  `ai_tools/config.py` does not define and will raise an `ImportError` — this is
  a known, pre-existing issue.
- **Supported code does not depend on this at import time.** The only link is
  `tools/hybrid_search.py` (the optional `/semantic` backend), which imports
  `experimental.ai_tools.*` lazily and only when the semantic extras are present.

## Related experimental code still under `tools/`

A cluster of analysis/agent modules under `tools/` (for example
`analyze_binary.py`, `tool_agent.py`, `investigation_loop.py`, the `*_agent.py`
files, `vector_indexer.py`) is also experimental, but it shares dependencies
with the supported deterministic report tool `tools/start_investigation.py`
through bare sibling imports. Splitting that cluster cleanly is a larger,
riskier change and was intentionally left for a follow-up; see
[current development state](../docs/current-state.md) for the supported-vs-experimental
breakdown.
