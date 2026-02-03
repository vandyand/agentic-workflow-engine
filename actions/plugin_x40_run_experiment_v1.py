from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict


X40_ROOT = Path("/home/kingjames/agents/x40_schemas")
RUN_SCRIPT = X40_ROOT / "x40_experiments" / "run_experiment.sh"


def _run_subprocess(args: list[str]) -> str:
    env = os.environ.copy()
    try:
        completed = subprocess.run(
            args,
            cwd=str(X40_ROOT),
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"run_experiment.sh failed: {' '.join(args)}\nstdout: {exc.stdout}\nstderr: {exc.stderr}"
        ) from exc
    return completed.stdout


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    exp_dir_input = resolved_input.get("expDir")
    port_input = resolved_input.get("port", 2600)

    if not isinstance(exp_dir_input, str) or not exp_dir_input.strip():
        raise ValueError("'expDir' must be a non-empty string")

    if isinstance(port_input, str):
        try:
            port = int(port_input)
        except ValueError as exc:
            raise ValueError("'port' must be an integer or numeric string") from exc
    elif isinstance(port_input, int):
        port = port_input
    else:
        raise ValueError("'port' must be an integer or numeric string")

    exp_dir_path = (
        Path(exp_dir_input)
        if Path(exp_dir_input).is_absolute()
        else X40_ROOT / exp_dir_input
    )

    if not exp_dir_path.exists():
        raise ValueError(f"experiment directory not found: {exp_dir_path}")

    if not RUN_SCRIPT.is_file():
        raise ValueError(f"run_experiment.sh not found at {RUN_SCRIPT}")

    stdout = _run_subprocess([str(RUN_SCRIPT), str(exp_dir_path), str(port)])

    metrics_path = exp_dir_path / "metrics.json"

    return {
        "stdout": stdout,
        "metricsPath": str(metrics_path),
        "expDir": str(exp_dir_path),
        "port": int(port),
    }


ACTION_META: Dict[str, Any] = {
    "plugin.x40.run_experiment": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["expDir"],
            "properties": {
                "expDir": {"type": "string"},
                "port": {"type": "integer"}
            },
            "additionalProperties": False
        },
        "outputSchema": {
            "type": "object",
            "required": ["stdout", "metricsPath"],
            "properties": {
                "stdout": {"type": "string"},
                "metricsPath": {"type": "string"},
                "expDir": {"type": "string"},
                "port": {"type": "integer"}
            },
            "additionalProperties": False
        }
    }
}


ACTIONS: Dict[str, Any] = {
    "plugin.x40.run_experiment": handler,
}
