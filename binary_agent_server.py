"""Local HTTP API for evidence-backed Ghidra exports.

The basic API has only two runtime requirements: Flask and an exported binary.
Semantic/LLM retrieval is deliberately optional and lazy so a missing model or
portable semantic index cannot stop direct local evidence work.
"""

from __future__ import annotations

import argparse
import hmac
import ipaddress
import os
import sys

from flask import Flask, Response, jsonify, request

from host_config import API_PORT, DEFAULT_EXPORT_PATH
from tools.local_evidence import EvidenceError, LocalEvidenceStore


ROUTE_CATALOG = [
    {"method": "GET", "route": "/health", "purpose": "Small liveness probe for monitors and scripts."},
    {"method": "GET", "route": "/status", "purpose": "Target identity, annotation count, and derived index capabilities."},
    {"method": "GET", "route": "/routes", "purpose": "Machine-readable route catalog."},
    {"method": "POST", "route": "/search", "purpose": "Search raw function metadata, accepted annotations, and optional FTS body text."},
    {"method": "POST", "route": "/lookup", "purpose": "Return one function evidence bundle with annotation, strings/imports, and callers/callees."},
    {"method": "POST", "route": "/function", "purpose": "Return the raw function document plus annotation summary."},
    {"method": "POST", "route": "/callers", "purpose": "Return direct callers for an address or exact function name."},
    {"method": "POST", "route": "/callees", "purpose": "Return direct callees for an address or exact function name."},
    {"method": "POST", "route": "/strings", "purpose": "Search exported strings and referencing functions."},
    {"method": "POST", "route": "/imports", "purpose": "Search imported APIs and referencing functions."},
    {"method": "POST", "route": "/trace", "purpose": "Generic static evidence trace for a term."},
    {"method": "POST", "route": "/asset", "purpose": "Trace a resource/asset term through exported strings and matching functions."},
    {"method": "POST", "route": "/control", "purpose": "Trace a UI/control-like name or ID through static evidence."},
    {"method": "POST", "route": "/packet", "purpose": "Find static packet-related evidence leads."},
    {"method": "POST", "route": "/class", "purpose": "Query the conservative derived class/vtable registry."},
    {"method": "POST", "route": "/review", "purpose": "Query non-promoting function-name review candidates."},
    {"method": "POST", "route": "/reload", "purpose": "Reload accepted annotations only."},
    {"method": "POST", "route": "/semantic", "purpose": "Optional semantic search leads."},
    {"method": "POST", "route": "/hybrid", "purpose": "Optional hybrid context leads."},
    {"method": "POST", "route": "/ask", "purpose": "Optional semantic context answer stub."},
]


def _request_data():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _error(message, status=400):
    return jsonify({"error": message}), status


def _json_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "y", "on"):
            return True
        if lowered in ("0", "false", "no", "n", "off"):
            return False
    return default


def _route_paths():
    return [item["route"] for item in ROUTE_CATALOG]


def _is_loopback_host(host):
    value = str(host or "").strip().lower()
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def _validate_bind(host, allow_remote, remote_token):
    if _is_loopback_host(host):
        return
    if not allow_remote:
        raise ValueError("Refusing non-loopback bind; pass --allow-remote explicitly")
    if not str(remote_token or "").strip():
        raise ValueError("A non-loopback bind requires GHIDRA_AI_REMOTE_TOKEN")


def create_app(export_path=None, remote_token=""):
    app = Flask(__name__)
    store = LocalEvidenceStore(export_path or DEFAULT_EXPORT_PATH)
    semantic = {"service": None, "error": None}
    auth_token = str(remote_token or "")

    @app.before_request
    def require_remote_token():
        if not auth_token:
            return None
        expected = "Bearer " + auth_token
        actual = request.headers.get("Authorization", "")
        if not hmac.compare_digest(actual, expected):
            return _error("Remote API authentication required", 401)
        return None

    def optional_semantic():
        if semantic["service"] is not None:
            return semantic["service"]
        if semantic["error"] is not None:
            raise RuntimeError(semantic["error"])
        try:
            from tools.hybrid_search import HybridSearch
            semantic["service"] = HybridSearch(store.export_path)
            return semantic["service"]
        except Exception:  # optional dependencies must not break core search
            app.logger.warning("Optional semantic search is unavailable", exc_info=True)
            semantic["error"] = "Optional semantic search is unavailable."
            raise RuntimeError(semantic["error"])

    @app.route("/", methods=["GET"])
    def index():
        """Human-readable entry point for browsers; API consumers use JSON routes."""
        return Response("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Binary Evidence API</title>
<style>body{max-width:760px;margin:3rem auto;font:16px/1.55 system-ui,sans-serif;color:#202020}code{background:#f1f1f1;padding:.15rem .3rem;border-radius:3px}a{color:#0758a8}li{margin:.35rem 0}</style>
</head><body><h1>Binary Evidence API</h1>
<p>This local service searches the exported Ghidra evidence corpus and its reviewed function-name annotations. It does not require Ghidra, embeddings, or an LLM for core lookups.</p>
<p><a href="/status">View target status (JSON)</a></p>
<h2>How to use it</h2><ol>
<li>Use <code>GET /health</code> for a small liveness check.</li>
<li>Use <code>GET /routes</code> to list supported routes.</li>
<li>Use <code>POST /search</code> to find function candidates.</li>
<li>Use <code>POST /lookup</code> to inspect raw evidence, accepted annotations, strings, imports, and call relationships.</li>
<li>Use <code>POST /asset</code>, <code>/control</code>, or <code>/packet</code> to trace static evidence leads.</li>
<li>Use <code>POST /class</code> for the conservative derived class/vtable registry, or <code>POST /review</code> for non-promoting name candidates.</li>
<li>After a reviewed annotation changes, use <code>POST /reload</code>.</li>
</ol>
<p>See <code>docs/local-evidence-api.md</code> in the exporter project for PowerShell examples and MCP setup. Semantic routes are optional leads, not ground truth.</p>
</body></html>""", mimetype="text/html")

    @app.errorhandler(EvidenceError)
    def handle_evidence_error(error):
        app.logger.info("Evidence request rejected: %s", error)
        return _error("Invalid or unavailable evidence request.", 400)

    @app.errorhandler(404)
    def handle_not_found(error):
        return _error("Unknown route. Use GET /routes for available endpoints.", 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return _error("Method is not allowed for this route. Use GET /routes for endpoint methods.", 405)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "online",
            "mode": "local-export",
            "export_path": store.export_path,
            "accepted_annotation_count": len(store._active_names),
        })

    @app.route("/status", methods=["GET"])
    def status():
        result = store.status()
        result["status"] = "online"
        result["routes"] = _route_paths()
        result["semantic_loaded"] = semantic["service"] is not None
        result["semantic_error"] = semantic["error"]
        return jsonify(result)

    @app.route("/routes", methods=["GET"])
    def routes():
        return jsonify({"routes": ROUTE_CATALOG})

    @app.route("/search", methods=["POST"])
    def search():
        data = _request_data()
        return jsonify(store.search(data.get("query", data.get("keyword", "")), data.get("limit", 20)))

    @app.route("/function", methods=["POST"])
    def function():
        data = _request_data()
        return jsonify(store.function(data.get("address", data.get("name", ""))))

    @app.route("/lookup", methods=["POST"])
    def lookup():
        data = _request_data()
        return jsonify(store.lookup(
            data.get("address", data.get("name", "")),
            _json_bool(data.get("include_decompiler"), True),
            _json_bool(data.get("include_assembly"), False),
            data.get("evidence_limit", 30),
        ))

    @app.route("/callers", methods=["POST"])
    def callers():
        data = _request_data()
        return jsonify(store.callers(data.get("address", data.get("name", ""))))

    @app.route("/callees", methods=["POST"])
    def callees():
        data = _request_data()
        return jsonify(store.callees(data.get("address", data.get("name", ""))))

    @app.route("/strings", methods=["POST"])
    def strings():
        data = _request_data()
        return jsonify(store.strings(data.get("query", data.get("keyword", "")), data.get("limit", 20)))

    @app.route("/imports", methods=["POST"])
    def imports():
        data = _request_data()
        return jsonify(store.imports(data.get("query", data.get("keyword", "")), data.get("limit", 20)))

    def traced(kind):
        data = _request_data()
        return jsonify(store.trace(data.get("term", data.get("query", data.get("keyword", ""))), kind, data.get("limit", 20)))

    @app.route("/trace", methods=["POST"])
    def trace():
        data = _request_data()
        return jsonify(store.trace(
            data.get("term", data.get("query", data.get("keyword", ""))),
            data.get("kind", "term"),
            data.get("limit", 20),
        ))

    @app.route("/asset", methods=["POST"])
    def asset():
        return traced("asset")

    @app.route("/control", methods=["POST"])
    def control():
        return traced("control")

    @app.route("/packet", methods=["POST"])
    def packet():
        return traced("packet-candidate")

    @app.route("/class", methods=["POST"])
    def class_info():
        data = _request_data()
        return jsonify(store.class_info(
            data.get("query", data.get("name", data.get("class", ""))),
            data.get("limit", 20),
        ))

    @app.route("/review", methods=["POST"])
    def review_queue():
        data = _request_data()
        return jsonify(store.review_queue(data.get("query", data.get("keyword", "")), data.get("limit", 20)))

    @app.route("/reload", methods=["POST"])
    def reload_annotations():
        # This is deliberately limited to the reviewable annotation overlay.
        # A changed raw export requires explicit validation and service restart.
        return jsonify(store.reload_annotations())

    @app.route("/semantic", methods=["POST"])
    def semantic_search():
        data = _request_data()
        try:
            result = optional_semantic().semantic(data.get("query", ""), data.get("limit", 10))
            return jsonify({"query": data.get("query", ""), "results": result, "mode": "optional-semantic"})
        except RuntimeError:
            return _error("Optional semantic search is unavailable.", 503)

    @app.route("/hybrid", methods=["POST"])
    def hybrid():
        data = _request_data()
        try:
            return jsonify({"query": data.get("query", ""), "result": optional_semantic().context(data.get("query", ""))})
        except RuntimeError:
            return _error("Optional semantic search is unavailable.", 503)

    @app.route("/ask", methods=["POST"])
    def ask():
        data = _request_data()
        question = data.get("question", "")
        try:
            context = optional_semantic().context(question)
            return jsonify({
                "question": question,
                "answer": "===== OPTIONAL SEMANTIC CONTEXT (NOT GROUND TRUTH) =====\n" + context[:12000],
            })
        except RuntimeError:
            return _error("Optional semantic search is unavailable.", 503)

    return app


def build_parser():
    parser = argparse.ArgumentParser(description="Serve a Ghidra export through the local evidence HTTP API.")
    parser.add_argument("--export", dest="export_path", default=DEFAULT_EXPORT_PATH, help="Export folder to serve.")
    parser.add_argument("--host", default=os.environ.get("GHIDRA_AI_BIND_HOST", "127.0.0.1"), help="Bind host.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("GHIDRA_AI_API_PORT", str(API_PORT))), help="Bind port.")
    parser.add_argument("--allow-remote", action="store_true", help="Allow a non-loopback bind when a remote token is configured.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        remote_token = os.environ.get("GHIDRA_AI_REMOTE_TOKEN", "")
        _validate_bind(args.host, args.allow_remote, remote_token)
        app = create_app(args.export_path, remote_token if not _is_loopback_host(args.host) else "")
    except (EvidenceError, OSError, ValueError) as error:
        print("[ERROR] {}".format(error), file=sys.stderr)
        return 1
    host = args.host
    port = args.port
    print("Binary Evidence API: http://{}:{}".format(host, port))
    # Never enable Flask's reloader here: it forks a second process, obscures
    # the real listener PID on Windows, and can leave an old local evidence
    # service running after a source update.
    app.run(host=host, port=port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
