#!/usr/bin/env python3
"""Budgeted, resumable local-model function-naming runner.

The model proposes JSON decisions. All writes still pass through the same
grounding guard and isolated candidate store as the MCP workflow.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import time
from typing import Any, Dict, Optional

import requests

from binary_agent_mcp_server import call_tool
from tools.agent_evidence import evidence_values
from tools import investigation_ledger as ledger
from tools.investigation_ledger import run_directory
from tools.local_evidence import LocalEvidenceStore
from tools.file_lock import locked_file


SYSTEM_PROMPT = """You are an evidence-first reverse-engineering naming agent.
Return exactly one JSON object. Never guess. The schema is:
{"action":"propose|skip|defer","name":"Symbol","confidence":"medium|high","evidence":["..."],"evidence_refs":["..."],"rationale":"...","note":"..."}
For propose, evidence_refs must be exact import names, string values, or named
caller/callee values copied verbatim from allowed_evidence_refs. Never use an
address as an evidence ref. Prefer skip to an inferred class, protocol, game
feature, or side effect. Do not include Markdown."""

RUN_CONFIG_NAME = "run_config.json"
RUN_CONFIG_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _json_object(text: str) -> Dict[str, Any]:
    value = str(text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", value, re.S | re.I)
    if fenced:
        value = fenced.group(1)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a JSON object")
        parsed = json.loads(value[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object")
    return parsed


class ModelResponseError(RuntimeError):
    """The provider replied, but the model output did not match the contract."""


class LocalModelClient:
    def __init__(self, endpoint: str, model: str, provider: str = "openai",
                 api_key: str = "", timeout: int = 300, temperature: float = 0.0,
                 retries: int = 2, max_tokens: int = 600,
                 context_window: int = 0):
        self.endpoint = endpoint
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self.retries = max(0, retries)
        self.max_tokens = max(64, int(max_tokens))
        self.context_window = max(0, int(context_window))

    def decide(self, lookup: Dict[str, Any]) -> Dict[str, Any]:
        user = "Name or skip this function using only this evidence:\n" + json.dumps(lookup, ensure_ascii=False)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        if self.provider == "ollama":
            options = {"temperature": self.temperature, "num_predict": self.max_tokens}
            if self.context_window:
                options["num_ctx"] = self.context_window
            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
                "stream": False,
                "format": "json",
                "options": options,
            }
        else:
            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
                "temperature": self.temperature,
                "stream": False,
                "max_tokens": self.max_tokens,
            }
        last_error: Optional[Exception] = None
        last_error_kind = "provider"
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                last_error = exc
                last_error_kind = "provider"
            else:
                try:
                    body = response.json()
                    if self.provider == "ollama":
                        content = body.get("message", {}).get("content", "")
                    else:
                        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return _json_object(content)
                except (ValueError, KeyError, IndexError, AttributeError) as exc:
                    last_error = exc
                    last_error_kind = "response"
            if attempt < self.retries:
                time.sleep(min(2 ** attempt, 5))
        message = "Local model request failed: {}".format(last_error)
        if last_error_kind == "response":
            raise ModelResponseError(message)
        raise RuntimeError(message)


def _bounded_lookup(store: LocalEvidenceStore, address: str, context_chars: int) -> Dict[str, Any]:
    lookup = store.lookup(address, include_decompiler=True, include_assembly=False)
    decompiler = lookup.get("decompiler", {}) or {}
    code = str(decompiler.get("c_code", ""))
    if len(code) > context_chars:
        code = code[:context_chars] + "\n/* truncated by overnight runner */"

    evidence = lookup.get("evidence", {}) or {}
    relationships = lookup.get("relationships", {}) or {}
    function = lookup.get("function", {}) or {}

    # The raw lookup contains useful API detail but also repeated metadata,
    # locals already present in the decompiler text, and large xref records.
    # Keep the unattended prompt compact so Ollama does not truncate the system
    # contract or JSON schema at modest runtime context sizes.
    allowed_refs = list(dict.fromkeys(evidence_values(lookup)))
    return {
        "target": lookup.get("target", {}),
        "function": {
            key: function.get(key)
            for key in ("address", "raw_name", "active_name", "namespace", "signature", "size", "parameters")
            if function.get(key) not in (None, "", [], {})
        },
        "evidence": {
            "strings": [
                {key: item.get(key) for key in ("value", "address") if item.get(key) not in (None, "")}
                for item in evidence.get("strings", []) or []
            ],
            "imports": [
                {key: item.get(key) for key in ("name", "library") if item.get(key) not in (None, "")}
                for item in evidence.get("imports", []) or []
            ],
            "comments": evidence.get("comments", []) or [],
        },
        "relationships": {
            direction: [
                {
                    key: item.get(key)
                    for key in ("address", "raw_name", "active_name", "name", "external")
                    if item.get(key) not in (None, "")
                }
                for item in relationships.get(direction, []) or []
            ]
            for direction in ("callers", "callees")
        },
        "allowed_evidence_refs": allowed_refs,
        "decompiler": {"success": bool(decompiler.get("success")), "c_code": code},
    }


def _append_log(export_path: str, run_id: str, event: Dict[str, Any]) -> None:
    directory = run_directory(export_path, run_id)
    os.makedirs(directory, exist_ok=True)
    event = dict(event, utc=_utc_now())
    path = os.path.join(directory, "runner.jsonl")
    with locked_file(path):
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _run_config_path(export_path: str, run_id: str) -> str:
    return os.path.join(run_directory(export_path, run_id), RUN_CONFIG_NAME)


def _write_run_config(store: LocalEvidenceStore, client: Any, run_id: str,
                      max_targets: int, max_minutes: float,
                      context_chars: int) -> None:
    """Persist the initial model settings once without exposing API secrets."""
    path = _run_config_path(store.export_path, run_id)
    config = {
        "schema_version": RUN_CONFIG_SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "run_id": run_id,
        "runner": "autonomous_naming_runner",
        "configuration": {
            "model": getattr(client, "model", None),
            "provider": getattr(client, "provider", None),
            "endpoint": getattr(client, "endpoint", None),
            "timeout_seconds": getattr(client, "timeout", None),
            "retries": getattr(client, "retries", None),
            "temperature": getattr(client, "temperature", None),
            "max_output_tokens": getattr(client, "max_tokens", None),
            "context_window": getattr(client, "context_window", None),
            "prompt_context_chars": context_chars,
            "max_targets": max_targets,
            "max_minutes": max_minutes,
        },
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(path):
        if os.path.exists(path):
            return
        with open(path, "x", encoding="utf-8", newline="\n") as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.write("\n")


def run_overnight(store: LocalEvidenceStore, client: Any, run_id: str,
                  max_targets: int = 100, max_minutes: float = 480,
                  context_chars: int = 12000, dry_run: bool = False) -> Dict[str, Any]:
    store.agent_run_id = run_id
    if not dry_run:
        _write_run_config(store, client, run_id, max_targets, max_minutes, context_chars)
    started = time.monotonic()
    processed = proposed = skipped = deferred = errors = invalid_decisions = fatal_errors = 0
    exhausted = False
    while processed < max(1, max_targets) and (time.monotonic() - started) < max_minutes * 60:
        target = ledger.next_target(store, store.export_path, run_id=run_id)
        if target is None:
            exhausted = True
            break
        lookup = _bounded_lookup(store, target["address"], context_chars)
        decision = None
        try:
            decision = client.decide(lookup)
        except (ModelResponseError, ValueError, AttributeError) as exc:
            reason = str(exc)
            recorded = ledger.record(store.export_path, target["address"], "deferred", reason, run_id)
            processed += 1
            deferred += 1
            errors += 1
            invalid_decisions += 1
            _append_log(store.export_path, run_id, {
                "event": "invalid-decision", "address": target["address"],
                "error": reason, "decision": decision, "result": recorded,
            })
            continue
        except (RuntimeError, OSError) as exc:
            errors += 1
            fatal_errors += 1
            _append_log(store.export_path, run_id, {
                "event": "provider-error", "address": target["address"], "error": str(exc),
            })
            break

        try:
            action = str(decision.get("action", "")).strip().lower()
            if dry_run:
                return {"dry_run": True, "target": target, "decision": decision, "writes": 0}
            if action == "propose":
                payload = call_tool(store, "binary_propose_name", {
                    "address": target["address"],
                    "name": decision.get("name", ""),
                    "confidence": decision.get("confidence", ""),
                    "evidence": decision.get("evidence", []) or [],
                    "evidence_refs": decision.get("evidence_refs", []) or [],
                    "rationale": decision.get("rationale", ""),
                })
                if payload.get("accepted"):
                    proposed += 1
                else:
                    deferred += 1
            elif action in ("skip", "defer"):
                status = "skipped" if action == "skip" else "deferred"
                ledger.record(store.export_path, target["address"], status, str(decision.get("note", "")), run_id)
                skipped += status == "skipped"
                deferred += status == "deferred"
                payload = {"accepted": False, "status": status}
            else:
                raise ValueError("Model action must be propose, skip, or defer")
            processed += 1
            _append_log(store.export_path, run_id, {"event": "decision", "address": target["address"], "decision": decision, "result": payload})
        except ValueError as exc:
            recorded = ledger.record(store.export_path, target["address"], "deferred", str(exc), run_id)
            processed += 1
            deferred += 1
            errors += 1
            invalid_decisions += 1
            _append_log(store.export_path, run_id, {
                "event": "invalid-decision", "address": target["address"],
                "error": str(exc), "decision": decision, "result": recorded,
            })
        except (RuntimeError, OSError) as exc:
            errors += 1
            fatal_errors += 1
            _append_log(store.export_path, run_id, {"event": "provider-error", "address": target["address"], "error": str(exc)})
            break
    return {
        "run_id": run_id,
        "processed": processed,
        "proposed": proposed,
        "skipped": skipped,
        "deferred": deferred,
        "errors": errors,
        "invalid_decisions": invalid_decisions,
        "fatal_errors": fatal_errors,
        "exhausted": exhausted,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "progress": ledger.summary(store, store.export_path, run_id),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a bounded local-model naming pass with isolated candidates.")
    parser.add_argument("export_path")
    parser.add_argument("--model", required=True, help="Local model name served by the endpoint.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1/chat/completions")
    parser.add_argument("--provider", choices=("openai", "ollama"), default="openai")
    parser.add_argument("--run-id", default="overnight")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--max-targets", type=int, default=100)
    parser.add_argument("--max-minutes", type=float, default=480)
    parser.add_argument("--context-chars", type=int, default=12000)
    parser.add_argument("--context-window", type=int, default=0,
                        help="Ollama runtime context tokens (num_ctx); 0 keeps the provider default.")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=600, help="Maximum model output tokens per target.")
    parser.add_argument("--dry-run", action="store_true", help="Ask for one decision and perform no writes.")
    args = parser.parse_args(argv)
    client = LocalModelClient(args.endpoint, args.model, args.provider, args.api_key, args.timeout,
                              args.temperature, args.retries, args.max_tokens, args.context_window)
    result = run_overnight(LocalEvidenceStore(args.export_path), client, args.run_id, args.max_targets, args.max_minutes, args.context_chars, args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("fatal_errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
