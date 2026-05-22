from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    """Get the real client IP, even when behind Render / Cloudflare proxies.

    `slowapi.util.get_remote_address` only looks at `request.client.host`,
    which on Render's PaaS is always the internal proxy IP — meaning every
    visitor world-wide would share one rate-limit bucket. Read the standard
    forwarded-for header instead, falling back to the direct connection.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    cf = request.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    return get_remote_address(request)

from . import database, examples, pdf_parser
from .models import (
    Answer,
    AskRequest,
    ChangeImpact,
    CompareRequest,
    DocumentMeta,
    ProviderInfo,
    RequirementsExtraction,
    Summary,
    UploadResponse,
)
from .providers import get_provider
from .providers.base import LLMProvider

logger = logging.getLogger("ai_doc_analyst")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    logger.info("Database initialized at %s", database.DB_PATH)
    yield


app = FastAPI(title="AI Document Analyst", version="0.3.0", lifespan=lifespan)

# Rate limiting. Per-IP sliding-window limits to protect the upstream Gemini /
# Claude free tier. Limits below are conservative — well under Gemini's 15 RPM
# free-tier cap so room is left for occasional bursts after deduplication.
limiter = Limiter(key_func=_client_ip, default_limits=[])
app.state.limiter = limiter
LLM_RATE_LIMIT = os.environ.get("LLM_RATE_LIMIT", "12/minute")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "You've sent requests too quickly. Please wait a moment and try again.",
            "retry_after_seconds": 60,
        },
        headers={"Retry-After": "60"},
    )

# CORS: in production the frontend on GitHub Pages calls a different origin
# from the backend on Render/Fly/etc. Allow specific origins from env (comma
# separated) plus sensible defaults for local dev and *.github.io.
_default_origins = [
    "http://localhost:8000",
    "http://localhost:8768",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8768",
]
_env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _env_origins,
    allow_origin_regex=r"https://[a-z0-9-]+\.github\.io",
    allow_credentials=False,
    allow_methods=["*"],
    # Explicit list (including the BYO-key headers) so browsers don't strip
    # them on preflight. `*` works for simple requests but the BYO-key
    # headers are non-standard and need to be enumerated here.
    allow_headers=["Content-Type", "X-Gemini-Key", "X-Anthropic-Key", "*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


def _provider(request: Request | None = None) -> LLMProvider:
    """Resolve the configured provider on every request.

    Re-reads env on every call (so LLM_PROVIDER can be flipped without a
    restart) and honors BYO-key headers from the frontend: if the visitor set
    their own key in the Settings panel, the frontend sends `X-Gemini-Key`
    (or `X-Anthropic-Key`) and we use that instead of the server's env-var key.
    """
    api_key_override: str | None = None
    if request is not None:
        name = os.environ.get("LLM_PROVIDER", "claude").strip().lower()
        header = "X-Gemini-Key" if name == "gemini" else "X-Anthropic-Key"
        api_key_override = request.headers.get(header) or None
    return get_provider(api_key_override=api_key_override)


@app.get("/health")
async def health():
    try:
        info = _provider().info().model_dump()
    except Exception as e:
        info = {"error": str(e)}
    return {"status": "ok", "provider": info}


@app.get("/provider", response_model=ProviderInfo)
async def provider_info():
    return _provider().info()


# ----- v2 endpoints -----

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    try:
        text = pdf_parser.extract_text(file.filename or "upload", file.content_type or "", raw)
    except Exception as e:
        logger.exception("PDF/text extraction failed")
        raise HTTPException(status_code=400, detail=f"Could not extract text: {e}") from e

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this file")

    meta = database.insert_document(
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(raw),
        text_content=text,
    )
    preview = text[:1500] + ("..." if len(text) > 1500 else "")
    return UploadResponse(document=meta, preview=preview)


@app.get("/documents", response_model=list[DocumentMeta])
async def documents():
    return database.list_documents()


@app.get("/examples")
async def list_examples():
    return examples.list_samples()


@app.post("/examples/{sample_id}/load", response_model=UploadResponse)
async def load_example(sample_id: int | str):
    loaded = examples.load_sample(str(sample_id))
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")
    filename, text = loaded
    meta = database.insert_document(
        filename=filename,
        content_type="text/markdown",
        size_bytes=len(text.encode("utf-8")),
        text_content=text,
    )
    preview = text[:1500] + ("..." if len(text) > 1500 else "")
    return UploadResponse(document=meta, preview=preview)


def _load_doc_text(doc_id: int) -> str:
    found = database.get_document_text(doc_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    _, text = found
    return text


def _handle_provider_error(e: Exception) -> HTTPException:
    """Map an upstream LLM exception to a user-safe HTTPException.

    The frontend will display the `detail` string verbatim, so it must not
    leak stack traces, internal config, or API key fragments.
    """
    msg = str(e)
    lower = msg.lower()
    logger.exception("Provider call failed")

    # Missing or bad API key — surface enough for the operator to fix it,
    # but not the key itself.
    if "api_key" in lower or "api key" in lower or "authentication" in lower:
        return HTTPException(
            status_code=503,
            detail="The model service isn't configured on this deployment. "
            "Please check back later.",
        )
    # Upstream model quota / per-minute rate limit / model not on this tier.
    # "limit: 0" is a deprecated-on-free-tier model rather than usage exhaustion.
    if "limit: 0" in lower:
        return HTTPException(
            status_code=503,
            detail="This deployment is configured to use a model that's not on the free tier. Please contact the demo owner.",
        )
    if "quota" in lower or ("rate" in lower and "limit" in lower) or "429" in msg or "resource_exhausted" in lower:
        return HTTPException(
            status_code=429,
            detail="The model's free-tier quota for today has been used up. Please try again in a few hours.",
        )
    # Schema-validation failure from messages.parse() / response_schema.
    if "validate" in lower or "pydantic" in lower or "did not return a valid" in lower:
        return HTTPException(
            status_code=502,
            detail="The model returned an unexpected response. Please try again.",
        )
    # Generic fallback — never expose raw upstream error text.
    return HTTPException(
        status_code=502,
        detail="The model is having trouble right now. Please try again in a moment.",
    )


@app.get("/summary/{doc_id}", response_model=Summary)
@limiter.limit(LLM_RATE_LIMIT)
async def summary(request: Request, doc_id: int, refresh: bool = Query(False, description="Bypass cache and re-run the model")):
    text = _load_doc_text(doc_id)
    if not refresh:
        cached = database.latest_query(doc_id, "summary")
        if cached:
            return Summary.model_validate_json(cached["response_json"])
    try:
        result = _provider(request).summarize(text)
    except Exception as e:
        raise _handle_provider_error(e) from e
    database.record_query(doc_id, "summary", None, result.model_dump_json())
    return result


@app.get("/requirements/{doc_id}", response_model=RequirementsExtraction)
@limiter.limit(LLM_RATE_LIMIT)
async def requirements(request: Request, doc_id: int, refresh: bool = Query(False, description="Bypass cache and re-run the model")):
    text = _load_doc_text(doc_id)
    if not refresh:
        cached = database.latest_query(doc_id, "requirements")
        if cached:
            return RequirementsExtraction.model_validate_json(cached["response_json"])
    try:
        result = _provider(request).extract_requirements(text)
    except Exception as e:
        raise _handle_provider_error(e) from e
    database.record_query(doc_id, "requirements", None, result.model_dump_json())
    return result


@app.post("/qa", response_model=Answer)
@limiter.limit(LLM_RATE_LIMIT)
async def qa(request: Request, body: AskRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    text = _load_doc_text(body.doc_id)
    try:
        result = _provider(request).answer_question(text, body.question)
    except Exception as e:
        raise _handle_provider_error(e) from e
    database.record_query(body.doc_id, "qa", body.question, result.model_dump_json())
    return result


@app.post("/compare", response_model=ChangeImpact)
@limiter.limit(LLM_RATE_LIMIT)
async def compare(request: Request, body: CompareRequest):
    if body.doc_id_before == body.doc_id_after:
        raise HTTPException(status_code=400, detail="doc_id_before and doc_id_after must differ")
    before = _load_doc_text(body.doc_id_before)
    after = _load_doc_text(body.doc_id_after)
    try:
        result = _provider(request).compare_documents(before, after)
    except Exception as e:
        raise _handle_provider_error(e) from e
    database.record_query(
        document_id=body.doc_id_before,
        secondary_document_id=body.doc_id_after,
        kind="compare",
        question=None,
        response_json=result.model_dump_json(),
    )
    return result


@app.get("/history")
async def history(doc_id: int | None = Query(None, description="Filter to one document"), limit: int = 100):
    if doc_id is not None and database.get_document_text(doc_id) is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return JSONResponse(database.list_queries(document_id=doc_id, limit=limit))


# Mount the static frontend last, so it doesn't shadow the API routes above.
# In production (GitHub Pages frontend + Render backend), this is dead weight —
# but it keeps `uvicorn app.main:app` a single command for local dev.
if DOCS_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DOCS_DIR), html=True), name="frontend")
