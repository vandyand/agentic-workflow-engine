from typing import Dict, Any, List

ACTIONS = {}

ACTION_META = {
    "plugin.transform.jq": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["data", "expression"],
            "properties": {
                "data": {},
                "expression": {"type": "string"}
            },
            "additionalProperties": False
        },
        "outputSchema": {
            "type": "object",
            "required": ["result"],
            "properties": {"result": {}},
            "additionalProperties": False
        }
    }
}


def _eval_single_expression(data: Any, expr: str) -> Any:
    """Evaluate a single jq expression (no pipes)."""
    expr = expr.strip()
    if not expr or expr == '.':
        return data

    # Handle special jq functions
    if expr == 'to_entries':
        if not isinstance(data, dict):
            raise ValueError("to_entries requires object input")
        return [{"key": k, "value": v} for k, v in data.items()]

    if expr == 'keys':
        if not isinstance(data, dict):
            raise ValueError("keys requires object input")
        return list(data.keys())

    if expr == 'values':
        if not isinstance(data, dict):
            raise ValueError("values requires object input")
        return list(data.values())

    if expr == 'length':
        if isinstance(data, (list, dict, str)):
            return len(data)
        raise ValueError("length requires array, object, or string")

    if expr == 'first':
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        raise ValueError("first requires non-empty array")

    if expr == 'last':
        if isinstance(data, list) and len(data) > 0:
            return data[-1]
        raise ValueError("last requires non-empty array")

    # Standard path expression starting with '.'
    if not expr.startswith('.'):
        raise ValueError(f"expression must start with '.' or be a function, got: {expr}")

    cur: Any = data
    # strip leading '.' then split by '.' while preserving [idx]
    tokens: List[str] = expr[1:].split('.') if expr != '.' else []
    for tok in tokens:
        if not tok:
            continue
        # handle array index in token like name[0] or [0]
        while tok:
            # compress nested brackets like '[[1]]' by shifting one
            if tok.startswith('[['):
                tok = tok[1:]
                continue
            if tok[0] == '[':
                # pure index at start
                end = tok.find(']')
                if end == -1:
                    raise ValueError("invalid index token")
                idx_str = tok[1:end].strip()
                try:
                    idx = int(idx_str)
                except Exception:
                    raise ValueError("invalid array index")
                if not isinstance(cur, list) or idx < 0 or idx >= len(cur):
                    return None
                cur = cur[idx]
                tok = tok[end+1:]
                continue
            # split head before next '['
            lb = tok.find('[')
            head = tok if lb == -1 else tok[:lb]
            if head:
                if not isinstance(cur, dict) or head not in cur:
                    raise ValueError(f"field not found: {head}")
                cur = cur[head]
            tok = tok[len(head):]
    return cur


def _eval_expression(data: Any, expr: str) -> Any:
    """Evaluate a jq expression, supporting pipes."""
    if not isinstance(expr, str) or not expr:
        raise ValueError("expression must be string")

    # Split by pipes and evaluate each part in sequence
    parts = [p.strip() for p in expr.split('|')]
    cur = data
    for part in parts:
        cur = _eval_single_expression(cur, part)
    return cur


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    data = resolved_input.get("data")
    expr = resolved_input.get("expression")
    if not isinstance(expr, str):
        raise ValueError("'expression' must be string")
    result = _eval_expression(data, expr)
    return {"result": result}


ACTIONS["plugin.transform.jq"] = handler
