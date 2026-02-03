# Auto-generated action handler for plugin.sqlite.create_table (v1)
from typing import Dict, Any

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    # Validate input
    if 'text' not in resolved_input:
        raise ValueError("Invalid input: 'text' field is required.")
    
    # Process input and create output
    output = {
        "text": f"Table created with input: {resolved_input['text']}"
    }
    
    return output

ACTIONS = {
    "plugin.sqlite.create_table": handler,
}
