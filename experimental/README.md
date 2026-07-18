# Experimental / unsupported

This directory contains legacy semantic/vector implementations, older agent
experiments, and ad-hoc scripts. It is retained for reference and is not part of
the supported evidence workflow.

For supported operation use the root scripts and `tools/` documented in the
[main README](../README.md) and [Getting started](../docs/getting-started.md).
Model guesses and semantic rankings are leads, never ground truth.

## Contents

| Path | Role |
| --- | --- |
| `ai_tools/` | Older vector, Chroma, graph, and retrieval helpers. |
| `vector_indexer.py`, `vector_query.py`, `llm_interface.py` | Deprecated duplicate semantic paths. |
| `reverse_engineering_agent.py`, `tool_agent.py` | Earlier agent experiments. |
| `build_embeddings_host.py`, `ai_tools/build_embeddings.py` | Compatibility wrappers for `revhub semantic-index`. |
| `legacy_tests/` | Unmaintained ad-hoc scripts; CI uses top-level `tests/`. |

## Boundaries

- Supported code does not import `experimental.*`.
- The supported optional backend is `tools/semantic_index.py`, producing one
  portable index under each export's `derived/semantic/` directory.
- Legacy modules may require packages no longer installed by the supported
  semantic extra and may retain fragile assumptions. Do not build new workflows
  on them.
- Package-qualified imports remain where these experiments call supported
  report/evidence modules, so their historical intent stays inspectable.

The maintained suite runs with `python -m unittest discover -s tests`.
