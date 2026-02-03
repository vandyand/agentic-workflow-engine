# Auto-generated action handler stub for plugin.transform.slugify (v1)
from typing import Dict, Any
import re


def _handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    text = resolved_input.get("text")
    sep = resolved_input.get("separator", "-")
    if not isinstance(text, str):
        raise ValueError("'text' must be a string")
    if not isinstance(sep, str) or not sep:
        sep = "-"
    slug = re.sub(r"[^a-zA-Z0-9]+", sep, text).strip(sep).lower()
    return {"text": slug}


ACTION_META = {
    "plugin.transform.slugify": {
        "version": "v1",
        "inputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}, "separator": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.transform.slugify": _handler,
}
