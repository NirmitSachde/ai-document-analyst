from __future__ import annotations

import io

import pdfplumber


def extract_text(filename: str, content_type: str, raw: bytes) -> str:
    name_lower = filename.lower()
    if content_type == "application/pdf" or name_lower.endswith(".pdf"):
        return _extract_pdf(raw)
    if content_type.startswith("text/") or name_lower.endswith((".txt", ".md", ".csv", ".log", ".json")):
        return raw.decode("utf-8", errors="replace")
    # Fall back to best-effort decode for unknown types
    return raw.decode("utf-8", errors="replace")


def _extract_pdf(raw: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"[Page {i}]\n{text}")
    return "\n\n".join(parts).strip()
