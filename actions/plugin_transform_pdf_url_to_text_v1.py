from __future__ import annotations

from typing import Any, Dict

import io
import requests

try:
    from pypdf import PdfReader
except Exception as exc:  # pragma: no cover - import error surfaced at runtime
    PdfReader = None  # type: ignore[assignment]


ACTION_META: Dict[str, Any] = {
    "plugin.transform.pdf_url_to_text": {
        "version": "v1",
        "inputSchema": {
            "type": "object",
            "required": ["pdf_url"],
            "properties": {
                "pdf_url": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
            },
            "additionalProperties": False,
        },
    }
}


def handler(node: Dict[str, Any], resolved_input: Dict[str, Any]) -> Dict[str, Any]:
    if PdfReader is None:
        raise ValueError("pypdf is not installed; install it to use pdf_url_to_text")

    pdf_url = resolved_input.get("pdf_url")
    if not isinstance(pdf_url, str) or not pdf_url.strip():
        raise ValueError("'pdf_url' must be a non-empty string")

    try:
        resp = requests.get(pdf_url, timeout=60)
    except requests.RequestException as exc:
        raise ValueError(f"Failed to download PDF from '{pdf_url}': {exc}") from exc

    if resp.status_code != 200:
        raise ValueError(f"PDF download HTTP {resp.status_code} from '{pdf_url}'")

    data = resp.content
    if not data:
        raise ValueError(f"Empty PDF response from '{pdf_url}'")

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"Failed to read PDF from '{pdf_url}': {exc}") from exc

    texts = []
    for page in getattr(reader, "pages", []) or []:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            texts.append(txt)

    text = "\n\n".join(texts).strip()
    if not text:
        raise ValueError(f"No extractable text found in PDF '{pdf_url}'")

    return {"text": text}


ACTIONS: Dict[str, Any] = {
    "plugin.transform.pdf_url_to_text": handler,
}

