from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
X40_ROOT = REPO_ROOT / "x40_schemas"
SCHEMAS_ROOT = X40_ROOT / "openai_json_schemas"

GEN_SCRIPT = SCHEMAS_ROOT / "openai_gen_json_schema.sh"
HYDRATE_SCRIPT = SCHEMAS_ROOT / "openai_json_of_schema.sh"
VET_SCRIPT = SCHEMAS_ROOT / "openai_schema_vetter.sh"


def _run_subprocess(args: list[str], env: dict[str, str] | None = None) -> str:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    try:
        completed = subprocess.run(
            args,
            env=effective_env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(X40_ROOT),
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Subprocess failed: {' '.join(args)}\nstdout: {exc.stdout}\nstderr: {exc.stderr}"
        ) from exc
    return completed.stdout.strip()


def _ensure_scripts_exist() -> None:
    missing: list[Path] = []
    for path in (GEN_SCRIPT, HYDRATE_SCRIPT, VET_SCRIPT):
        if not path.is_file():
            missing.append(path)
    if missing:
        joined = ", ".join(str(p) for p in missing)
        raise ValueError(f"Required schema helper scripts not found: {joined}")


def _handler_generate_from_prompt(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_scripts_exist()
    description = resolved_input.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("'description' must be a non-empty string")

    model = resolved_input.get("model")
    verbose = bool(resolved_input.get("verbose", False))
    save_path = resolved_input.get("savePath")
    skip_vet = bool(resolved_input.get("skipVet", False))
    if save_path is not None and not isinstance(save_path, str):
        raise ValueError("'savePath' must be a string when provided")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_schema_path = Path(tmp_dir) / "raw_schema.json"
        cmd: list[str] = [str(GEN_SCRIPT), "--message", description]
        if isinstance(model, str) and model.strip():
            cmd.extend(["--model", model.strip()])
        cmd.extend(["--outputfile", str(tmp_schema_path)])
        if verbose:
            cmd.append("--verbose")

        _run_subprocess(cmd)

        vetted_schema_path: Path
        if skip_vet:
            vetted_schema_path = tmp_schema_path
        else:
            vetted_schema_path = Path(tmp_dir) / "vetted_schema.json"
            vet_cmd: list[str] = [
                str(VET_SCRIPT),
                "--schema",
                str(tmp_schema_path),
                "--outputfile",
                str(vetted_schema_path),
            ]
            if verbose:
                vet_cmd.append("--verbose")
            _run_subprocess(vet_cmd)

        with open(vetted_schema_path, "r", encoding="utf-8") as f:
            final_schema = json.load(f)

    result: Dict[str, Any] = {"schema": final_schema}

    if save_path:
        save_path_obj = Path(save_path)
        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path_obj, "w", encoding="utf-8") as f_save:
            json.dump(final_schema, f_save, indent=2)
        result["path"] = str(save_path_obj)

    return result


def _handler_vet(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_scripts_exist()
    schema = resolved_input.get("schema")
    if not isinstance(schema, dict):
        raise ValueError("'schema' must be an object")

    with tempfile.TemporaryDirectory() as tmp_dir:
        candidate_path = Path(tmp_dir) / "candidate_schema.json"
        output_path = Path(tmp_dir) / "vetted_schema.json"
        with open(candidate_path, "w", encoding="utf-8") as f:
            json.dump(schema, f)

        cmd: list[str] = [
            str(VET_SCRIPT),
            "--schema",
            str(candidate_path),
            "--outputfile",
            str(output_path),
        ]
        _run_subprocess(cmd)

        with open(output_path, "r", encoding="utf-8") as f_out:
            vetted_schema = json.load(f_out)

    return {"schema": vetted_schema}


def _handler_hydrate(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_scripts_exist()
    prompt = resolved_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("'prompt' must be a non-empty string")

    schema_obj = resolved_input.get("schema")
    schema_path_input = resolved_input.get("schemaPath")
    model = resolved_input.get("model")
    strict_flag = resolved_input.get("strict")
    skip_vet = bool(resolved_input.get("skipVet", False))

    if schema_path_input is not None and not isinstance(schema_path_input, str):
        raise ValueError("'schemaPath' must be a string when provided")

    if schema_obj is None and not schema_path_input:
        raise ValueError("Either 'schema' or 'schemaPath' must be provided")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        if schema_path_input:
            schema_path = Path(schema_path_input)
            if not schema_path.is_file():
                raise ValueError(f"Schema file not found: {schema_path}")
        else:
            if not isinstance(schema_obj, dict):
                raise ValueError("'schema' must be an object when provided")
            raw_schema_path = tmp_dir_path / "input_schema.json"
            with open(raw_schema_path, "w", encoding="utf-8") as f_in:
                json.dump(schema_obj, f_in)

            if skip_vet:
                schema_path = raw_schema_path
            else:
                vetted_schema_path = tmp_dir_path / "vetted_schema.json"
                vet_cmd: list[str] = [
                    str(VET_SCRIPT),
                    "--schema",
                    str(raw_schema_path),
                    "--outputfile",
                    str(vetted_schema_path),
                ]
                _run_subprocess(vet_cmd)
                schema_path = vetted_schema_path

        cmd: list[str] = [
            str(HYDRATE_SCRIPT),
            "--schema",
            str(schema_path),
            "--message",
            prompt,
        ]
        if isinstance(model, str) and model.strip():
            cmd.extend(["--model", model.strip()])
        if strict_flag is True:
            cmd.append("--strict")
        elif strict_flag is False:
            cmd.append("--no-strict")

        raw_output = _run_subprocess(cmd)

    text = raw_output.strip()
    parsed: Any
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = text

    return {"result": parsed}


ACTION_META: Dict[str, Any] = {
    "plugin.schema.generate_from_prompt": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {"type": "string"},
                "model": {"type": "string"},
                "savePath": {"type": "string"},
                "verbose": {"type": "boolean"},
                "skipVet": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["schema"],
            "properties": {
                "schema": {"type": "object"},
                "path": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "plugin.schema.vet": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["schema"],
            "properties": {"schema": {"type": "object"}},
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["schema"],
            "properties": {"schema": {"type": "object"}},
            "additionalProperties": False,
        },
    },
    "plugin.schema.hydrate": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "schema": {"type": "object"},
                "schemaPath": {"type": "string"},
                "model": {"type": "string"},
                "strict": {"type": "boolean"},
                "skipVet": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["result"],
            "properties": {"result": {}},
            "additionalProperties": False,
        },
    },
}


ACTIONS: Dict[str, Any] = {
    "plugin.schema.generate_from_prompt": _handler_generate_from_prompt,
    "plugin.schema.vet": _handler_vet,
    "plugin.schema.hydrate": _handler_hydrate,
}
