from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent / "examples"


# Hand-curated metadata so the frontend can show a friendly name and a short
# blurb explaining what each sample is good for demoing.
SAMPLES: list[dict] = [
    {
        "id": "prd-v1",
        "filename": "prd-orderflow-v1.md",
        "label": "PRD: OrderFlow v1.0",
        "description": "B2B checkout platform PRD with explicit functional / non-functional requirements, dates, action items, and entities. Good for Summarize and Extract Requirements.",
    },
    {
        "id": "prd-v2",
        "filename": "prd-orderflow-v2.md",
        "label": "PRD: OrderFlow v2.0",
        "description": "Updated PRD with scope changes, a new ML routing requirement, tightened SLAs, and dropped freemium tier. Pair with v1 to demo Change Impact.",
    },
    {
        "id": "sow",
        "filename": "sow-acme-implementation.md",
        "label": "Statement of Work: Acme implementation",
        "description": "Fixed-price consulting SOW with phased milestones, payment triggers, assumptions, and signatures. Good for Q&A (e.g. \"what is the pilot acceptance criteria?\").",
    },
]


def list_samples() -> list[dict]:
    """Return sample metadata, omitting samples whose files are missing."""
    available = []
    for s in SAMPLES:
        if (_ROOT / s["filename"]).is_file():
            available.append({k: v for k, v in s.items() if k != "filename"})
    return available


def load_sample(sample_id: str) -> tuple[str, str] | None:
    """Return (filename, text) for the given sample id, or None if missing."""
    for s in SAMPLES:
        if s["id"] == sample_id:
            path = _ROOT / s["filename"]
            if path.is_file():
                return s["filename"], path.read_text(encoding="utf-8")
    return None
