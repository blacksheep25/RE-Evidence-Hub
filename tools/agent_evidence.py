"""Deterministic evidence checks for autonomous/agent-recorded findings.

A model proposing a function name must cite concrete evidence refs — an import
name, a string value, or the name of a function it calls. This module verifies
each cited ref appears as a WHOLE TOKEN among that function's discrete evidence
values, so a hallucinated or generic justification is rejected before it becomes
an accepted annotation. The model is treated as untrusted and made to prove its
claim against the export.

Deliberately narrow, by design:
- Only discrete evidence VALUES are checkable: import names, string values, and
  the names of *named* callees/callers. Decompiler pseudo-code, assembly, and the
  function's own auto-generated ``FUN_`` name are NOT checkable — matching against
  them let ubiquitous tokens (``mov``, ``param_1``, ``return``, ``FUN_``) rubber-
  stamp any name.
- Matching is whole-token (word boundary), case-insensitive — so citing ``key``
  does not spuriously match ``turkey`` and a ref only counts if the model
  actually saw that concrete value.

This verifies a citation is grounded; it cannot prove the chosen name is the
*best* name. It is a floor against fabrication, not a correctness oracle.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

MIN_REF_LEN = 3
SYMBOL_PATTERN = re.compile(r"^[A-Za-z_~?$@][A-Za-z0-9_:$@?<>~.\-]{0,127}$")


def evidence_values(lookup: Dict[str, Any]) -> List[str]:
    """Return the discrete evidence values a citation may reference.

    Import names, string values, and named (non-``FUN_``) callee/caller names
    from a LocalEvidenceStore.lookup bundle. Intentionally excludes decompiler
    c_code, assembly, signature, and the function's own placeholder name.
    """
    values: List[str] = []
    evidence = lookup.get("evidence", {}) or {}
    for item in evidence.get("imports", []) or []:
        name = str(item.get("name", "")).strip()
        if name:
            values.append(name)
    for item in evidence.get("strings", []) or []:
        value = str(item.get("value", "")).strip()
        if value:
            values.append(value)
    relationships = lookup.get("relationships", {}) or {}
    for item in (relationships.get("callees", []) or []) + (relationships.get("callers", []) or []):
        for key in ("active_name", "raw_name"):
            name = str(item.get(key) or "").strip()
            if name and not name.startswith("FUN_"):
                values.append(name)
    return values


def _contains_token(haystack_lower: str, ref_lower: str) -> bool:
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(ref_lower) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, haystack_lower) is not None


def verify_evidence_refs(lookup: Dict[str, Any], refs: List[str]) -> Tuple[bool, List[str]]:
    """Check each cited ref is grounded in the function's discrete evidence.

    Returns ``(all_grounded, missing)``. Refs shorter than ``MIN_REF_LEN`` are
    rejected as too generic. A ref is grounded only if
    it appears as a whole token within an import name, string value, or named
    callee/caller (see :func:`evidence_values`).
    """
    normalized = [str(ref).strip() for ref in (refs or [])]
    if not normalized or not any(normalized):
        return False, []
    invalid = [ref for ref in normalized if len(ref) < MIN_REF_LEN]
    if invalid:
        return False, invalid
    haystack = "\n".join(evidence_values(lookup)).lower()
    missing = [ref for ref in normalized if not _contains_token(haystack, ref.lower())]
    return (len(missing) == 0, missing)


def validate_annotation_proposal(name: str, confidence: str, evidence: List[str],
                                 rationale: str, refs: List[str]) -> Tuple[bool, str]:
    """Apply the acceptance policy after refs have been grounded.

    Citation grounding is necessary but not sufficient: unattended writes also
    need a usable symbol, reviewable reasoning, and either a reference linked to
    the proposed name or multiple independent concrete references.
    """
    proposed = str(name or "").strip()
    if not proposed or not SYMBOL_PATTERN.fullmatch(proposed) or proposed.startswith("FUN_"):
        return False, "name must be a non-placeholder symbol without whitespace or control characters"
    if confidence not in ("medium", "high"):
        return False, "autonomous accepted annotations require medium or high confidence"

    evidence_lines = [str(item).strip() for item in (evidence or []) if str(item).strip()]
    if not evidence_lines:
        return False, "at least one human-readable evidence line is required"
    explanation = str(rationale or "").strip()
    if len(explanation) < 12:
        return False, "a concrete rationale of at least 12 characters is required"

    distinct_refs = {str(ref).strip().lower() for ref in (refs or []) if str(ref).strip()}
    name_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9]+", proposed)}
    compact_name = re.sub(r"[^a-z0-9]", "", proposed.lower())
    linked = any(
        ref in name_terms or re.sub(r"[^a-z0-9]", "", ref) in compact_name
        for ref in distinct_refs
    )
    if not linked and len(distinct_refs) < 2:
        return False, "one citation must support a name term, or two independent evidence refs are required"
    return True, ""
