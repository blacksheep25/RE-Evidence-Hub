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
    ignored as too generic; a call with no usable ref returns ``(False, [])`` so
    a citation of only short/empty tokens is rejected. A ref is grounded only if
    it appears as a whole token within an import name, string value, or named
    callee/caller (see :func:`evidence_values`).
    """
    usable = [str(ref).strip() for ref in (refs or []) if len(str(ref).strip()) >= MIN_REF_LEN]
    if not usable:
        return False, []
    haystack = "\n".join(evidence_values(lookup)).lower()
    missing = [ref for ref in usable if not _contains_token(haystack, ref.lower())]
    return (len(missing) == 0, missing)
