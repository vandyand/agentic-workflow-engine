from __future__ import annotations

from typing import Any, Dict

import os
import requests


ACTION_META: Dict[str, Any] = {
    "plugin.llm.complete": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["model", "prompt"],
            "properties": {
                "model": {"type": "string"},
                "prompt": {"type": "string"},
                "max_tokens": {"type": "integer"},
                "temperature": {"type": "number"},
                "context": {},
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
            "additionalProperties": False,
        },
    }
}


def _is_ollama_model(model: str) -> bool:
    # Heuristic: local Ollama models are usually short names with optional tag,
    # e.g. "llama3.2:latest", "gemma3:1b", without a "/" path.
    return "/" not in model


def _call_ollama(model: str, prompt: str, max_tokens: int | None, temperature: float | None) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    url = f"{base_url.rstrip('/')}/api/generate"

    options: Dict[str, Any] = {}
    if max_tokens is not None:
        # Ollama uses num_predict for max tokens to generate
        options["num_predict"] = int(max_tokens)
    if temperature is not None:
        options["temperature"] = float(temperature)

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if options:
        payload["options"] = options

    try:
        resp = requests.post(url, json=payload, timeout=120)
    except requests.RequestException as exc:
        raise ValueError(f"Ollama request failed: {exc}") from exc

    if resp.status_code != 200:
        raise ValueError(f"Ollama HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        data = resp.json()
    except Exception as exc:
        raise ValueError(f"Invalid JSON from Ollama: {resp.text[:200]}") from exc

    # /api/generate returns a single JSON object with 'response'
    text = data.get("response")
    if not isinstance(text, str):
        raise ValueError(f"Ollama response missing 'response' text: {data}")
    return text


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    model = resolved_input.get("model")
    prompt = resolved_input.get("prompt")
    context = resolved_input.get("context")
    max_tokens = resolved_input.get("max_tokens")
    temperature = resolved_input.get("temperature")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("'model' must be a non-empty string")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("'prompt' must be a non-empty string")

    if max_tokens is not None and not isinstance(max_tokens, int):
        raise ValueError("'max_tokens' must be an integer if provided")
    if temperature is not None and not isinstance(temperature, (int, float)):
        raise ValueError("'temperature' must be a number if provided")

    # Optionally append structured or string context to the prompt.
    if context is not None:
        try:
            import json as _json  # local import to avoid hard dependency at module import time
            if isinstance(context, dict):
                ctx_str = _json.dumps(context, indent=2, ensure_ascii=False)
            else:
                ctx_str = str(context)
            prompt = f"{prompt.rstrip()}\n\n--- CONTEXT ---\n{ctx_str}"
        except Exception:
            # If context can't be serialized, fall back to plain string conversion.
            prompt = f"{prompt.rstrip()}\n\n--- CONTEXT ---\n{context}"

    # For now, we support local Ollama models only. If you pass a remote
    # model path with '/', this will raise to avoid silently doing nothing.
    if not _is_ollama_model(model):
        raise ValueError(
            f"Model '{model}' looks like a remote provider path; "
            f"plugin.llm.complete currently supports only local Ollama models."
        )

    text = _call_ollama(model=model, prompt=prompt, max_tokens=max_tokens, temperature=temperature)
    return {"text": text}


ACTIONS: Dict[str, Any] = {
    "plugin.llm.complete": handler,
}

