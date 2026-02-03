from typing import Dict, Any
import requests

ACTIONS = {}

ACTION_META = {
    "plugin.http.get": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "params": {"type": "object"},
                "headers": {"type": "object"}
            },
            "additionalProperties": False
        },
        "outputSchema": {
            "type": "object",
            "required": ["status", "body"],
            "properties": {
                "status": {"type": "integer"},
                "body": {}
            },
            "additionalProperties": False
        }
    }
}


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    url = resolved_input.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError("'url' must be a non-empty string")
    params = resolved_input.get("params") if isinstance(resolved_input.get("params"), dict) else None
    headers = resolved_input.get("headers") if isinstance(resolved_input.get("headers"), dict) else None
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        status = resp.status_code
        body: Any
        # Try JSON first, fall back to text
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return {"status": int(status), "body": body}
    except requests.RequestException as e:
        # Surface as a permanent error for the node
        raise ValueError(f"http.get request failed: {e}")


ACTIONS["plugin.http.get"] = handler
