# Auto-generated action handler stub for plugin.html.extract_xml (v1)
from typing import Dict, Any

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    if 'text' not in resolved_input:
        raise ValueError("Input must contain 'text' field")

    text = resolved_input['text']
    # Simple XML extraction using string manipulation
    extracted_xml = ''
    in_tag = False
    for char in text:
        if char == '<':
            in_tag = True
            extracted_xml += char
        elif char == '>':
            in_tag = False
            extracted_xml += char
        elif in_tag:
            extracted_xml += char

    return {'text': extracted_xml}

ACTION_META = {
    "plugin.html.extract_xml": {
        "version": "v1",
        "inputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.html.extract_xml": handler,
}
