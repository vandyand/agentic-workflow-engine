# Action handler for plugin.core.echo (v1)
from typing import Dict, Any

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    message = resolved_input.get("message")
    if not isinstance(message, str):
        message = "" if message is None else str(message)
    if message.strip() == "":
        message = "(no result)"
    return {"message": message}

ACTION_META = {
    "plugin.core.echo": {
        "version": "v1",
        "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "additionalProperties": True},
        "outputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "additionalProperties": True},
    }
}

ACTIONS = {
    "plugin.core.echo": handler,
}
