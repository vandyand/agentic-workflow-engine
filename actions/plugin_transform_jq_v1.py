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


def _eval_expression(data: Any, expr: str) -> Any:
    # Minimal evaluator for expressions like .a.b[0].c
    if not isinstance(expr, str) or not expr:
        raise ValueError("expression must be string")
    # support simple pipelines by truncating at first '|'
    if '|' in expr:
        expr = expr.split('|', 1)[0].strip()
    if not expr.startswith('.'):
        raise ValueError("expression must start with '.'")
    cur: Any = data
    # strip leading '.' then split by '.' while preserving [idx]
    tokens: List[str] = expr[1:].split('.') if expr != '.' else []
    for tok in tokens:
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
                    raise ValueError("field not found")
                cur = cur[head]
            tok = tok[len(head):]
    return cur


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    data = resolved_input.get("data")
    expr = resolved_input.get("expression")
    if not isinstance(expr, str):
        raise ValueError("'expression' must be string")
    result = _eval_expression(data, expr)
    return {"result": result}


ACTIONS["plugin.transform.jq"] = handler
