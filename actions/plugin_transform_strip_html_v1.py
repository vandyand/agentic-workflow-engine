from typing import Dict, Any
import re


def _handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    """Strip HTML tags from input text.

    Accepts either 'text' or 'html' string fields; returns {'text': <stripped>}.
    """
    src = resolved_input.get("text")
    if not isinstance(src, str):
        src = resolved_input.get("html")
    if not isinstance(src, str):
        raise ValueError("Expected 'text' or 'html' string input")
    # Remove tags and collapse whitespace
    stripped = re.sub(r"<[^>]*>", "", src)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return {"text": stripped}


ACTION_META = {
    "plugin.transform.strip_html": {
        "version": "v1",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "html": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.transform.strip_html": _handler,
}
