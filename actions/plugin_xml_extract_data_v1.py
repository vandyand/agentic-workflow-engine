# Auto-generated action handler stub for plugin.xml.extract_data (v1)
from typing import Dict, Any
import xml.etree.ElementTree as ET

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    if 'text' not in resolved_input:
        raise ValueError("Input must contain 'text' field")

    try:
        root = ET.fromstring(resolved_input['text'])
        extracted_data = []
        for elem in root:
            if elem.text is not None:
                extracted_data.append(elem.text)
        return {'text': '\n'.join(extracted_data)}
    except ET.ParseError as e:
        raise ValueError("Invalid XML input") from e

ACTION_META = {
    "plugin.xml.extract_data": {
        "version": "v1",
        "inputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False},
    }
}

ACTIONS = {
    "plugin.xml.extract_data": handler,
}
