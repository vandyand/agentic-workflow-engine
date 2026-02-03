# Auto-generated action handler stub for plugin.core.timeout (v1)
from typing import Dict, Any

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    if 'text' not in resolved_input:
        raise ValueError("Input must contain 'text' field")
    return {'text': resolved_input['text'] + ' timed out'}

ACTIONS = {
    "plugin.core.timeout": handler,
}
