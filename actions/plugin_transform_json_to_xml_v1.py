# Auto-generated action handler stub for plugin.transform.json_to_xml (v1)
from typing import Dict, Any
import json
import xml.etree.ElementTree as ET

def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        json_text = resolved_input.get('text')
        if not json_text:
            raise ValueError("Input 'text' is required")

        json_data = json.loads(json_text)
        root = ET.Element("root")
        _json_to_xml(json_data, root)
        xml_text = ET.tostring(root, encoding='unicode')

        return {'text': xml_text}

    except Exception as e:
        raise ValueError(f"Failed to transform JSON to XML: {str(e)}")

def _json_to_xml(json_data, parent_element):
    if isinstance(json_data, dict):
        for key, value in json_data.items():
            child_element = ET.SubElement(parent_element, key)
            _json_to_xml(value, child_element)
    elif isinstance(json_data, list):
        for value in json_data:
            child_element = ET.SubElement(parent_element, 'item')
            _json_to_xml(value, child_element)
    else:
        parent_element.text = str(json_data)

ACTIONS = {
    "plugin.transform.json_to_xml": handler,
}
