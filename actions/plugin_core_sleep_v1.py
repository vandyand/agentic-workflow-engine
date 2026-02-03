# Auto-generated action handler stub for plugin.core.sleep (v1)
from typing import Dict, Any
import time

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    if 'duration' not in resolved_input:
        raise ValueError("Missing required input field 'duration'")

    try:
        duration = int(resolved_input['duration'])
    except ValueError:
        raise ValueError("Invalid input field 'duration', must be an integer")

    if duration < 0:
        raise ValueError("Invalid input field 'duration', must be a non-negative integer")

    time.sleep(duration)
    return {'text': f'Slept for {duration} seconds'}

ACTION_META = {
    "plugin.core.sleep": {
        "version": "v1",
        "inputSchema": {"type": "object", "required": ["duration"], "properties": {"duration": {"type": "integer", "minimum": 0}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.core.sleep": handler,
}
