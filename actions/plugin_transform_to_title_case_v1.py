# Auto-generated action handler stub for plugin.transform.to_title_case (v1)
from typing import Dict, Any


def _handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    text = resolved_input.get("text")
    if not isinstance(text, str):
        raise ValueError("'text' must be a string")
    return {"text": text.title()}


ACTION_META = {
    "plugin.transform.to_title_case": {
        "version": "v1",
        "inputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.transform.to_title_case": _handler,
}
