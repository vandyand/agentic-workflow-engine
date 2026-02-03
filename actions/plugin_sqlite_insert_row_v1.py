# Auto-generated action handler for plugin.sqlite.insert_row (v1)
from typing import Dict, Any

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    # Validate input
    if 'text' not in resolved_input:
        raise ValueError("Invalid input: 'text' field is required")
    
    # Process input and create output
    output = {
        "status": "success",
        "text": resolved_input['text'],  # Ensure output includes 'text'
        "message": f"Inserted row with text: {resolved_input['text']}"
    }
    
    return output

ACTIONS = {
    "plugin.sqlite.insert_row": handler,
}
