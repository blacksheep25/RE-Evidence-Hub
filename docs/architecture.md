# Architecture and Data Contract

This document is the technical reference. If you are new to the project, start
with [Getting started](getting-started.md), then return here when you need file
schemas, entry points, or extension points.

## Boundaries

The project has two runtime boundaries.

1. **Ghidra export runtime.** `run_exporter.py` is executed by Ghidra's Script
   Manager.  It receives `currentProgram` and `monitor` from Ghidra, then
   invokes `AIExporter` and `ExportPipeline`.
2. **Host analysis runtime.** Scripts in `tools/`, the top-level API scripts,
   and the unsupported helpers under `experimental/` (see
   [experimental/README.md](../experimental/README.md)) run under a normal
   Python 3 installation.  They
   consume an already-created export directory and may need third-party Python
   packages or a running local LLM service.

Do not cross these boundaries casually: the exporter imports Ghidra Java APIs,
while host search and agent code imports packages such as Chroma, NumPy,
`sentence-transformers`, Flask, and Requests.

### Project workspace boundary

`project_layout.py` is dependency-free and shared by PyGhidra and host Python.
The default root is `project_exports/`, with one manifest-bearing directory per
program. `RE_EVIDENCE_PROJECTS_ROOT` relocates it; explicit paths and the saved
current-export pointer remain compatible.

Inside one export, raw evidence is immutable, `derived/` is rebuildable,
`annotations/` contains reviewed reversible conclusions, and
`agent_runs/<run-id>/` contains disposable autonomous work. Promotion from an
agent run to annotations requires explicit review.

## Core pipeline

`ExportPipeline.run()` executes the following stages in this order.  Each stage
is isolated: a failing stage is added to `export_report.json`, and later stages
are still attempted.

| Stage | Source | Output | Contents |
| --- | --- | --- | --- |
| Manifest | `ManifestExporter` | `manifest.json` | Binary name, project domain file, original source path, input hashes when available, image base, executable format, language/compiler IDs, memory blocks, function count. |
| Memory | `MemoryExporter` | `memory_map.json` | Block ranges, permissions, initialization, mapping, source, comment. |
| Imports/exports | `ImportExporter` | `imports.json`, `exports.json` | External functions and their caller references; external entry-point symbols. |
| Types | `DataTypeExporter` | `types/*.json` | Structures, unions, enums, and typedefs. |
| Globals | `GlobalExporter` | `globals.json` | Defined data outside a block literally named `.text`, including references and referring functions. |
| Strings | `StringExporter` | `strings.json` | Defined Ghidra `StringDataType` values with references and referring functions. |
| Functions | `FunctionExporter` | `functions/<address>.json` | The primary per-function evidence record. |
| Call graph | `CallGraphExporter` | `callgraph.json` | Function nodes and deduplicated edges discovered from instruction flows. |
| Markdown summaries | `AISummaryExporter` | `markdown/<address>.md` | Human-readable function pages. |
| Search index | `SearchIndexExporter` | `index.json` | Address-keyed function index plus name-to-address lookup, and indexes for strings, imports, types, and globals. |
| AI context | `AIContextExporter` | `ai_context.json` | Dataset description and analysis guidance. |
| Heuristic summaries | `FunctionSummaryExporter` | `function_summaries.json` | Small descriptions based on called API names, not model-generated summaries. |
| Pipeline report | `ExportPipeline` | `export_report.json` | Stage name, status, elapsed time, and errors where present. |

The enabled flags in `Config` control the memory/import/type/global/string/
callgraph/decompiler/xref/comment collection stages.  Functions and the four
derived stages are currently always invoked by `pipeline.py`; this is a known
implementation detail rather than a configurable feature.

Manifest exporter version 1.1 adds `binary.source_path`, optional input-file
`md5`/`sha256` values, and `compiler.id`. It retains `binary.domain_file` and
`compiler.name` for compatibility with 1.0 consumers. New consumers should use
the stable compiler ID and treat the Java-style compiler name as legacy data.

## Per-function record

Every `functions/<address>.json` is the authoritative function document.  Its
top-level fields are:

| Field | Meaning |
| --- | --- |
| `address`, `name`, `namespace`, `external` | Function identity as Ghidra currently knows it. |
| `range`, `size`, `instruction_count`, `hash` | Address range and basic size metrics. `hash` is SHA-256 of exported assembly text. |
| `signature`, `return_type`, `parameters`, `locals` | Recovered type and variable information. |
| `assembly` | One formatted instruction per line. |
| `decompiler` | `success`, `c_code`, and decompiler-derived locals where decompilation completed; otherwise failure information. |
| `calls`, `called_by` | Function relations identified from instruction flows and call references. |
| `xrefs` | References to the entry point when enabled. |
| `comments` | EOL comments found while iterating instructions when enabled. |

Addresses are serialised as Ghidra string representations and are also the
function filename.  Consumers must preserve that representation exactly rather
than converting it to an integer.

`index.json` version 2 uses those addresses as the `functions` object keys;
each entry also includes its current name and relative JSON file path. The
separate `function_names` object maps a name to all matching addresses. This
preserves duplicate C++ symbols rather than silently discarding them.

## Derived and analysis files

The export process creates a useful static dataset, but the host analysis tools
can create further files in the same export folder:

| Producer | Extra output |
| --- | --- |
| `tools/binary_triage.py` | `triage_report.json`, `triage_report.md` |
| `tools/evidence_collector.py` | `evidence_database.json` |
| `tools/startup_analyzer.py` | `startup_analysis.json`, `startup_analysis.md` |
| `experimental/callgraph_agent.py` | `callgraph_analysis.json` |
| `experimental/analysis_agent.py` | `analysis_report.json`, `analysis_report.md` |
| `tools/report_generator.py` | `reverse_engineering_report.json`, `reverse_engineering_report.md` |
| `tools/investigation_memory.py` | `investigation_memory.json` |
| `tools/start_investigation.py` | `investigation_session.json` |
| `tools/function_annotations.py` | `annotations/function_names.json`, `annotations/function_names.md` |
| `tools/build_local_index.py` | `local_evidence.sqlite3` (optional, derived FTS5 index; trigram tokenizer for substring body search) |
| `tools/generate_evidence_pack.py` | `evidence_packs/<topic>.json` (derived binary + Media review pack) |
| `tools/build_class_registry.py` | `class_registry.json` (derived class/RTTI/vtable review registry; vtable ownership only from explicit accepted evidence) |
| `tools/build_name_review_queue.py` | `name_review_queue.json` (derived, non-promoting direct import/resource naming candidates) |
| `exporters/embedding_exporter.py` / `experimental/build_chunks.py` | `ai_chunks.json` |
| `experimental/vector_indexer.py` | `vectors/embeddings.npy`, `vectors/metadata.json` |
| `experimental/build_embeddings_host.py` | A separate Chroma collection called `ghidra` |

## Host entry points

| Command | Purpose | Main prerequisites |
| --- | --- | --- |
| `python tools/start_investigation.py <export>` | Triage, evidence collection, startup report, consolidated report, and empty investigation memory. | Core export. |
| `python experimental/analyze_binary.py <export>` | Alternative pipeline: vector index, subsystem report, call-graph analysis, startup, evidence, final report. | Core export plus `ai_chunks.json` for its first step. |
| `python tools/validate_export.py <export> --full` | Verifies required files, index identity, function count, and all function records. | Core export. |
| `python experimental/build_chunks.py <export>` | Creates `ai_chunks.json` from raw function JSON without rerunning Ghidra. | Core export. |
| `python experimental/query_engine.py <export> <query>` | Searches `ai_chunks.json` by lexical scoring. | `ai_chunks.json`. |
| `python experimental/vector_indexer.py <export>` | Builds local NumPy vectors with `all-MiniLM-L6-v2`. | `ai_chunks.json`, NumPy, sentence-transformers. |
| `python experimental/vector_query.py <export> <query>` | Searches local NumPy vectors. | `vectors/` output from the indexer. |
| `python experimental/build_embeddings_host.py` | Rebuilds the configured Chroma collection using BGE embeddings. | Edit hard-coded paths; Chroma and sentence-transformers. |
| `python binary_agent_server.py --export <export>` | Starts the local evidence JSON API on `127.0.0.1:5006`. | Core export and Flask; semantic routes load optional dependencies only when called. |
| `python binary_agent_mcp_server.py --export <export>` | Starts the read-only stdio MCP adapter. | Core export only. |
| `python tools/build_local_index.py <export>` | Builds the optional fast local FTS5 body-search index. | Core export. |
| `python tools/generate_evidence_pack.py <title> ...` | Creates a bounded, reviewable evidence pack. | Core export; accepted annotations recommended. |
| `python tools/build_class_registry.py <export>` | Builds a conservative class/vtable registry from globals and accepted annotations. | Core export, `globals.json`, annotations optional. |
| `python tools/build_name_review_queue.py <export>` | Builds non-promoting name candidates from direct import/resource evidence. | Core export, strings/imports optional, annotations optional. |
| `python experimental/tool_agent.py <export> <api-url> <model>` | Interactive JSON-tool-call loop using the same local evidence core as HTTP/MCP. | Core export, Requests, compatible model API. |

`tools/evidence_tools.py` is the in-process adapter and direct CLI for Python
agents and scripts. It wraps `LocalEvidenceStore` directly rather than calling
the Flask service, so local workflows do not depend on a port or background
process.
`tools/evidence_client.py` is the small HTTP client for scripts that
intentionally need to talk to an already-running `binary_agent_server.py`.
The older `AnalysisTools` class remains as a compatibility facade over
`EvidenceTools`; new code should prefer `EvidenceTools` unless it explicitly
needs the old list-shaped method names.

The Flask service exposes `GET /health`, `GET /status`, `GET /routes`, and
`POST` routes `/search`, `/function`, `/lookup`, `/callers`, `/callees`,
`/strings`, `/imports`, `/trace`, `/asset`, `/control`, `/packet`, `/class`,
`/review`, `/reload`, `/semantic`, `/hybrid`, and `/ask`. Core routes return
raw evidence plus accepted reversible annotations. Semantic routes are optional
leads and are not required to start the service.

## Safe extension points

- Add a new raw Ghidra export as an exporter class, then register it in
  `pipeline.py` and document its output in the tables above.
- Add an export flag to `Config`, and include it in `Config.dump()` and the
  pipeline report.
- Treat raw function JSON as the source of truth.  Derived indexes and reports
  can be safely regenerated from it.
- Keep source data and analysis artefacts separate in naming and avoid silently
  overwriting the raw function files.
- Keep inferred function names in an annotation overlay until a reviewed Ghidra
  rename pass is explicitly requested. The overlay stores address, function
  assembly hash, confidence, evidence, and replacement history separately from
  raw exports.
