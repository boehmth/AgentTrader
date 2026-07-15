# runner/refs.py — Auflösung von "$results[i].key.subkey".
#
# Wenn der LLM in einem Step-Argument eine Referenz auf ein früheres Ergebnis
# einfügt (Format: "$results[<index>].<key>[.<subkey>...]"), löst diese Datei
# den Wert vor dem Tool-Call auf.

import re
from typing import Any, Dict, List

# Vollständige Referenz: der ganze String ist ein Ref, z. B. "$results[0].cash".
_REF_FULL_RE = re.compile(r"^\$results\[(\d+)\]\.([A-Za-z0-9_\.\-]+)$")
# Eingebettete Referenz: findet $results[i].path in einem längeren String
# wie "12@$results[1].latest.close" oder "shares=12@$results[3].result".
# Der Pfad matcht Buchstaben/Ziffern/Unterstrich/Punkt/Minus.
_REF_EMBED_RE = re.compile(r"\$results\[(\d+)\]\.([A-Za-z0-9_\.\-]+)")


def _lookup(idx: int, path: str, results: List[Any]) -> Any:
    if idx < 0 or idx >= len(results):
        return f"__ref_error__:index {idx} out of range"
    node: Any = results[idx]
    for key in path.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list) and key.lstrip("-").isdigit():
            i = int(key)
            if -len(node) <= i < len(node):
                node = node[i]
            else:
                return f"__ref_error__:index '{key}' out of range"
        else:
            return f"__ref_error__:key '{key}' not found"
    return node


def resolve_ref(value: Any, results: List[Any]) -> Any:
    """Löst Referenzen der Form $results[i].key.subkey auf.

    Zwei Modi:
      1) Voll-Match: der ganze String ist eine Referenz -> gib den Wert zurück
         (als String, falls numerisch, sonst das Objekt selbst).
      2) Eingebettet: der String enthält eine Referenz als Teil-Ausdruck
         (z. B. '12@$results[1].latest.close') -> ersetze die Referenz
         durch ihren Wert als Text; der Rest bleibt.
    """
    if not isinstance(value, str):
        return value

    s = value.strip()

    # 1) Voll-Match
    m_full = _REF_FULL_RE.match(s)
    if m_full:
        val = _lookup(int(m_full.group(1)), m_full.group(2), results)
        return str(val) if isinstance(val, (int, float)) else val

    # 2) Eingebettete Substitutionen
    def _sub(m):
        val = _lookup(int(m.group(1)), m.group(2), results)
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return val
        # dict/list in einem String zu inlinen ist nicht sinnvoll
        return f"__ref_error__:cannot inline non-scalar"

    substituted = _REF_EMBED_RE.sub(_sub, value)
    return substituted


def resolve_args(args: Dict[str, Any], results: List[Any]) -> Dict[str, Any]:
    return {k: resolve_ref(v, results) for k, v in args.items()}
