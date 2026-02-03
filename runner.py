#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


ROOT = os.path.dirname(__file__)
PARENT = os.path.dirname(ROOT)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
ACTIONS_DIR = os.path.join(ROOT, "actions")


def _read_ir(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        if (path.endswith(".yaml") or path.endswith(".yml")) and yaml is not None:
            return yaml.safe_load(f)
        return json.load(f)


def _topo_order(nodes: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    indeg: Dict[str, int] = {}
    by_id: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        nid = n["id"]
        by_id[nid] = n
        indeg.setdefault(nid, 0)
    for n in nodes:
        for d in (n.get("dependsOn") or []):
            indeg[n["id"]] = indeg.get(n["id"], 0) + 1
    q = [nid for nid, deg in indeg.items() if deg == 0]
    order: List[str] = []
    while q:
        cur = q.pop(0)
        order.append(cur)
        for n in nodes:
            if cur in (n.get("dependsOn") or []):
                indeg[n["id"]] -= 1
                if indeg[n["id"]] == 0:
                    q.append(n["id"])
    cycles = [nid for nid, deg in indeg.items() if deg > 0]
    return order, cycles


def _resolve_ref(path: str, context: Dict[str, Dict[str, Any]]) -> Any:
    # Supports $.nodes.<id>.output.<field>[.<subfield>...]
    parts = path.split(".")
    if len(parts) < 5 or parts[0] != "$" or parts[1] != "nodes" or parts[3] != "output":
        raise PermanentError(f"Unsupported $ref path: {path}")
    nid = parts[2]
    if nid not in context:
        raise RetryableError(f"$ref to unknown node: {nid}")
    val: Any = context[nid]
    if os.environ.get('AUTOMATOR_DEBUG_REF') == '1':
        try:
            import json as _json
            print(f"[DEBUG_REF] nid={nid} out=" + _json.dumps(val)[:200])
        except Exception:
            pass
    # Skip 'output' token at index 3
    for token in parts[4:]:
        # Support tokens with array index like 'result[0]' or pure '[0]'
        if '[' in token and token.endswith(']'):
            head, idx_str = token.split('[', 1)
            idx_str = idx_str[:-1]
            if head:
                if not (isinstance(val, dict) and head in val):
                    raise PermanentError(f"$ref field not found: {path}")
                val = val[head]
            try:
                idx = int(idx_str)
            except Exception:
                raise PermanentError(f"$ref invalid index: {path}")
            if not (isinstance(val, list) and 0 <= idx < len(val)):
                raise PermanentError(f"$ref index out of range: {path}")
            val = val[idx]
        else:
            if isinstance(val, dict) and token in val:
                val = val[token]
            else:
                raise PermanentError(f"$ref field not found: {path}")
    return val


def _resolve_input(obj: Any, context: Dict[str, Dict[str, Any]]) -> Any:
    if isinstance(obj, dict):
        if set(obj.keys()) == {"$ref"} and isinstance(obj["$ref"], str):
            return _resolve_ref(obj["$ref"], context)
        return {k: _resolve_input(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_input(v, context) for v in obj]
    if isinstance(obj, str):
        # Guard: disallow template literals in verify/prod
        mode = os.environ.get("AUTOMATOR_MODE", "explore")
        if mode in ("verify", "prod") and "{{" in obj and "}}" in obj:
            raise PermanentError("template literals not allowed in verify/prod; use $ref")
    return obj


def _load_actions() -> Dict[Tuple[str, str], Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]]:
    """Return mapping of (actionRef, schemaVersion) -> handler."""
    mapping: Dict[Tuple[str, str], Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {}
    if not os.path.isdir(ACTIONS_DIR):
        return mapping
    for name in os.listdir(ACTIONS_DIR):
        if not name.endswith(".py"):
            continue
        mod_name = name[:-3]
        if mod_name.startswith("__"):
            continue
        try:
            mod = importlib.import_module(f"automator.actions.{mod_name}")
        except Exception:
            continue
        actions = getattr(mod, "ACTIONS", {})
        if not isinstance(actions, dict):
            continue
        for action_ref, handler in actions.items():
            if not callable(handler):
                continue
            # Derive version from filename suffix _vX
            ver = "v1"
            if "_v" in mod_name:
                try:
                    ver = "v" + mod_name.split("_v", 1)[1]
                except Exception:
                    ver = "v1"
            mapping[(action_ref, ver)] = handler
    return mapping


def _execute_node(handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]], node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    return handler(node, resolved_input)


def _mock_handler(action_ref: str) -> Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]:
    def http_get(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        # Provide both 'body' and 'json' with minimal expected structure
        json_obj = {"query": {"search": [{"title": "Mock Title 1"}, {"title": "Mock Title 2"}]}}
        return {"status": 200, "body": json_obj, "json": json_obj}

    def http_post(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": 200, "body": {"mock": True}}

    def files_write(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        content = inp.get('content')
        b = len(content.encode('utf-8')) if isinstance(content, str) else 0
        return {"bytesWritten": b}

    def jq(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        # Return a simple deterministic result
        data = inp.get('data')
        return {"result": data if data is not None else []}

    def llm_complete(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        prompt = inp.get('prompt')
        text = "Mock summary" if not isinstance(prompt, str) else f"Mock: {prompt[:20]}"
        return {"text": text}

    # SQLite mocks to enable verify/shadow runs without real implementations
    def sqlite_create_db(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        db_path = inp.get('path') or '/tmp/mock.sqlite'
        return {"status": "ok", "path": db_path}

    def sqlite_create_table(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        table = inp.get('table') or 'mock_table'
        return {"status": "ok", "table": table}

    def sqlite_insert_row(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ok", "rowId": 1}

    def sqlite_query(node: Dict[str, Any], inp: Dict[str, Any]) -> Dict[str, Any]:
        # Return deterministic rows structure
        return {"status": "ok", "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

    mapping = {
        'plugin.http.get': http_get,
        'plugin.http.post': http_post,
        'plugin.files.write': files_write,
        'plugin.transform.jq': jq,
        'plugin.llm.complete': llm_complete,
        # sqlite action family mocks
        'plugin.sqlite.create_db': sqlite_create_db,
        'plugin.sqlite.create_table': sqlite_create_table,
        'plugin.sqlite.insert_row': sqlite_insert_row,
        'plugin.sqlite.query': sqlite_query,
    }
    return mapping.get(action_ref)


def main() -> None:
    ap = argparse.ArgumentParser(description="Automator runner")
    ap.add_argument("workflow", help="Path to workflow IR (yaml/json)")
    ap.add_argument("--dry-run", action="store_true", help="Do not execute actions; just validate graph order and input resolution")
    ap.add_argument("--mode", choices=["explore", "verify", "prod"], default=os.environ.get("AUTOMATOR_MODE", "explore"))
    ap.add_argument("--mock-io", action="store_true", help="Mock external side effects like HTTP and file writes")
    args = ap.parse_args()

    wf_path = os.path.abspath(args.workflow)
    ir = _read_ir(wf_path)
    if not isinstance(ir, dict) or ir.get("kind") != "process":
        print("NODE_FAILED: invalid IR")
        raise SystemExit(2)
    nodes: List[Dict[str, Any]] = ir.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        print("NODE_FAILED: no nodes")
        raise SystemExit(2)

    order, cycles = _topo_order(nodes)
    if cycles:
        print("NODE_FAILED: cycle detected: " + ", ".join(cycles))
        raise SystemExit(3)

    id_to_node = {n["id"]: n for n in nodes}
    actions = _load_actions()
    mock_io = args.mock_io or (args.mode == 'verify' and os.environ.get('AUTOMATOR_MOCK_IO', '0') == '1')
    # Load quarantine list
    quarantine: set[tuple[str, str]] = set()
    try:
        qfile = os.path.join(ROOT, 'quarantine', 'actions.jsonl')
        with open(qfile, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    quarantine.add((obj.get('actionRef'), obj.get('version') or 'v1'))
                except Exception:
                    continue
    except Exception:
        pass
    runs_dir = os.environ.get('AUTOMATOR_RUNS_DIR', os.path.join(ROOT, 'runs'))
    try:
        os.makedirs(runs_dir, exist_ok=True)
    except Exception:
        pass
    metrics_path = os.path.join(runs_dir, 'metrics.jsonl')

    context_outputs: Dict[str, Dict[str, Any]] = {}

    for nid in order:
        node = id_to_node[nid]
        action_ref = node.get("actionRef")
        schema_version = node.get("schemaVersion", "v1")
        if not isinstance(action_ref, str):
            print(f"NODE_FAILED: {nid}: invalid actionRef")
            raise SystemExit(3)
        handler = actions.get((action_ref, schema_version))
        if mock_io and handler is None:
            # Allow mock handler even if real one isn't implemented
            mh = _mock_handler(action_ref)
            handler = mh  # type: ignore
        if handler is None:
            print(f"NODE_FAILED: {nid}: action not implemented: {action_ref}:{schema_version}")
            raise SystemExit(3)
        if mock_io:
            # For known external effects, substitute with mock handler
            mock = _mock_handler(action_ref)
            if mock is not None and mock is not (lambda n, i: {}):
                handler = mock  # type: ignore
        if (action_ref, schema_version) in quarantine and args.mode in ('verify','prod'):
            print(f"NODE_FAILED: {nid}: action quarantined: {action_ref}:{schema_version}")
            raise SystemExit(4)

        if args.dry_run:
            # In dry-run, skip input resolution and execution; assume node can run
            context_outputs[nid] = {"dryRun": True}
            continue

        try:
            resolved_input = _resolve_input(node.get("input") or {}, context_outputs)
        except RetryableError as e:
            print(f"NODE_FAILED: {nid}: {e}")
            raise SystemExit(4)
        except PermanentError as e:
            print(f"NODE_FAILED: {nid}: {e}")
            raise SystemExit(4)

        # Timeouts and retries
        retry_cfg = node.get("retry") or {}
        max_attempts = int(retry_cfg.get("maxAttempts", 1))
        backoff_ms = int(retry_cfg.get("backoffMs", 0))
        timeout_ms = int(node.get("timeoutMs") or 0)

        attempt = 0
        while True:
            attempt += 1
            try:
                if timeout_ms > 0:
                    # Cooperative timeout: measure wall time
                    start = time.time()
                    out = _execute_node(handler, node, resolved_input)
                    elapsed_ms = int((time.time() - start) * 1000)
                    if elapsed_ms > timeout_ms:
                        raise RetryableError(f"timeout exceeded: {elapsed_ms}ms > {timeout_ms}ms")
                else:
                    out = _execute_node(handler, node, resolved_input)
                if not isinstance(out, dict):
                    raise PermanentError("handler must return object")
                context_outputs[nid] = out
                try:
                    with open(metrics_path, 'a', encoding='utf-8') as mf:
                        mf.write(json.dumps({'type': 'node_result', 'node': nid, 'actionRef': action_ref, 'schemaVersion': schema_version, 'ok': True}) + "\n")
                except Exception:
                    pass
                break
            except RetryableError as e:
                if attempt >= max_attempts:
                    print(f"NODE_FAILED: {nid}: {e}")
                    print(traceback.format_exc())
                    try:
                        with open(metrics_path, 'a', encoding='utf-8') as mf:
                            mf.write(json.dumps({'type': 'node_result', 'node': nid, 'actionRef': action_ref, 'schemaVersion': schema_version, 'ok': False, 'error': str(e)}) + "\n")
                    except Exception:
                        pass
                    raise SystemExit(4)
                time.sleep(max(0, backoff_ms) / 1000.0)
                continue
            except PermanentError as e:
                print(f"NODE_FAILED: {nid}: {e}")
                print(traceback.format_exc())
                try:
                    with open(metrics_path, 'a', encoding='utf-8') as mf:
                        mf.write(json.dumps({'type': 'node_result', 'node': nid, 'actionRef': action_ref, 'schemaVersion': schema_version, 'ok': False, 'error': str(e)}) + "\n")
                except Exception:
                    pass
                raise SystemExit(4)
            except Exception as e:
                # Unknown exceptions are treated as retryable by default
                if attempt >= max_attempts:
                    print(f"NODE_FAILED: {nid}: {e}")
                    print(traceback.format_exc())
                    try:
                        with open(metrics_path, 'a', encoding='utf-8') as mf:
                            mf.write(json.dumps({'type': 'node_result', 'node': nid, 'actionRef': action_ref, 'schemaVersion': schema_version, 'ok': False, 'error': str(e)}) + "\n")
                    except Exception:
                        pass
                    raise SystemExit(4)
                time.sleep(max(0, backoff_ms) / 1000.0)
                continue

    try:
        with open(metrics_path, 'a', encoding='utf-8') as mf:
            mf.write(json.dumps({'type': 'workflow_result', 'workflow': os.path.abspath(wf_path), 'ok': True}) + "\n")
    except Exception:
        pass
    print("OK")


if __name__ == "__main__":
    main()
