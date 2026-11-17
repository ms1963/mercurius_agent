"""
Fuzzy Parameter Healing and Type Coercion for Mercurius Tools.
Inspired by Hermes Agent schema robustness: heals parameter typos,
synonyms, and casts types automatically before tool execution.
"""
from __future__ import annotations
import difflib
from typing import Any, Dict, List, Tuple

SYNONYM_MAP = {
    "url": ["link", "target_url", "uri", "webpage", "site", "address"],
    "query": ["q", "search_query", "term", "keyword", "prompt", "text"],
    "path": ["filepath", "file_path", "filename", "file", "target_path"],
    "content": ["data", "text", "body", "payload"],
    "num_results": ["limit", "count", "num", "max_results", "k"],
    "command": ["cmd", "script", "bash_command", "code"],
}

def heal_parameters(expected_params: Dict[str, Any], received_args: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Auto-heals received tool arguments against expected parameters schema.
    Returns (healed_args, list_of_corrections_made).
    """
    corrections = []
    properties = expected_params.get("properties", {})
    required = expected_params.get("required", [])
    healed: Dict[str, Any] = {}

    expected_keys = list(properties.keys())
    unmatched_received = dict(received_args)

    # 1. Direct matches with type coercion
    for key, spec in properties.items():
        if key in unmatched_received:
            val = unmatched_received.pop(key)
            healed[key] = _coerce_type(val, spec.get("type"))
            continue

        # 2. Synonym matching
        matched_synonym = None
        for syn in SYNONYM_MAP.get(key, []):
            if syn in unmatched_received:
                matched_synonym = syn
                break

        if matched_synonym:
            val = unmatched_received.pop(matched_synonym)
            healed[key] = _coerce_type(val, spec.get("type"))
            corrections.append(f"Mapped synonym '{matched_synonym}' -> '{key}'")
            continue

        # 3. Fuzzy Levenshtein match for small typos
        closest = difflib.get_close_matches(key, list(unmatched_received.keys()), n=1, cutoff=0.7)
        if closest:
            wrong_key = closest[0]
            val = unmatched_received.pop(wrong_key)
            healed[key] = _coerce_type(val, spec.get("type"))
            corrections.append(f"Auto-healed typo '{wrong_key}' -> '{key}'")

    # Keep any extra arguments just in case
    for k, v in unmatched_received.items():
        healed[k] = v

    return healed, corrections

def _coerce_type(val: Any, target_type: str | None) -> Any:
    if target_type is None:
        return val
    try:
        if target_type == "integer" and not isinstance(val, int):
            return int(float(val))
        elif target_type == "number" and not isinstance(val, (int, float)):
            return float(val)
        elif target_type == "boolean" and not isinstance(val, bool):
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "t")
            return bool(val)
        elif target_type == "string" and not isinstance(val, str):
            return str(val)
    except (ValueError, TypeError):
        return val
    return val
