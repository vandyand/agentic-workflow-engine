# Action handler for plugin.files.write (v1)
from typing import Dict, Any
import os


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    path = resolved_input.get("path")
    content = resolved_input.get("content")
    overwrite = bool(resolved_input.get("overwrite", True))
    if not isinstance(path, str) or not isinstance(content, str):
        raise ValueError("'path' and 'content' must be strings")
    if os.path.exists(path) and not overwrite:
        raise ValueError("file exists and overwrite is false")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = content.encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)
    return {"bytesWritten": len(data)}


ACTION_META = {
    "plugin.files.write": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["path", "content"],
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}},
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["bytesWritten"],
            "properties": {"bytesWritten": {"type": "integer", "minimum": 0}},
            "additionalProperties": False,
        },
    }
}

ACTIONS = {
    "plugin.files.write": handler,
}
