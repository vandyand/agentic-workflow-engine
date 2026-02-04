from typing import Dict, Any
import xmltodict

ACTIONS = {}

ACTION_META = {
    "plugin.transform.xml2json": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["xml"],
            "properties": {
                "xml": {"type": "string"}
            },
            "additionalProperties": False
        },
        "outputSchema": {
            "type": "object",
            "required": ["json"],
            "properties": {
                "json": {}
            },
            "additionalProperties": False
        }
    }
}


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    xml_text = resolved_input.get("xml")
    if not isinstance(xml_text, str) or not xml_text.strip():
        raise ValueError("'xml' must be a non-empty string")
    try:
        result = xmltodict.parse(xml_text)
        return {"json": result}
    except Exception as e:
        raise ValueError(f"Failed to parse XML: {e}")


ACTIONS["plugin.transform.xml2json"] = handler
