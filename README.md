# AI Document Analyst

A FastAPI web app that takes uploaded business documents (PDFs, text, CSV) and uses an LLM to:

- **Summarize** — overview, key points, named entities, action items, dates
- **Extract requirements** — structured requirements (ID, description, priority, category, dependencies) from PRDs / specs / user stories
- **Answer questions** — natural-language Q&A grounded in the uploaded document, with citations
- **Change impact analysis** — compare two versions of the same document, surface added / removed / modified requirements, with rationale and a risk level for stakeholder review

The LLM backend is pluggable — pick **Claude** (Anthropic) or **Gemini** (Google) via the `LLM_PROVIDER` env var.

## Architecture

```
┌──────────────┐       ┌─────────────────────────────────┐       ┌─────────────────────────────┐
│   Browser    │ ────▶ │   FastAPI app                   │ ────▶ │  LLM provider               │
│   (HTML/JS)  │ ◀──── │   /upload /summary /requirements│ ◀──── │  claude-sonnet-4-6   OR     │
└──────────────┘       │   /qa /compare /history         │       │  gemini-2.0-flash           │
                       │                                 │       └─────────────────────────────┘
                       │  pdfplumber → text extraction   │
                       │  SQLite     → docs + queries    │
                       └─────────────────────────────────┘
```

Layout:

- `app/main.py` — FastAPI app, endpoints, lifespan-managed SQLite init, CORS middleware
- `app/pdf_parser.py` — PDF/text extraction via `pdfplumber`
- `app/providers/` — pluggable LLM backend (`base.py`, `claude.py`, `gemini.py`)
- `app/database.py` — SQLite schema and queries; lazy-caches the latest summary/requirements per doc
- `app/models.py` — Pydantic models used for both API responses and LLM structured outputs
- `docs/` — static frontend (`index.html`, `app.js`, `style.css`). Served by FastAPI at `/` for local dev; also served directly by GitHub Pages for hosted deployments.

## Running locally

Requires Python 3.11+ (developed with 3.13).

```bash
cp .env.example .env
# edit .env: set LLM_PROVIDER and the API key for the chosen provider

python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. Frontend and API are on the same origin, so the Settings panel can stay blank.

## Deploying (GitHub Pages frontend + Render backend)

The frontend is fully static and lives under `docs/`. The backend is a Python service.

### 1. Push the repo to GitHub

```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin git@github.com:<you>/ai-document-analyst.git
git push -u origin main
```

### 2. Deploy the backend to Render

1. Sign in at <https://render.com> with your GitHub account.
2. Click **New +** → **Blueprint**. Point it at this repo. Render reads [render.yaml](render.yaml) and creates a service from the Dockerfile.
3. After the first deploy, open the service in the dashboard and set the **environment variables**:
   - `GEMINI_API_KEY` — your Gemini key (or `ANTHROPIC_API_KEY` if you set `LLM_PROVIDER=claude`)
   - `CORS_ORIGINS` — your GitHub Pages origin, e.g. `https://<yourname>.github.io`
4. Note the public URL (e.g. `https://ai-doc-analyst.onrender.com`). You'll paste this into the frontend's Settings panel.

**Free tier caveats:**
- The service **sleeps after 15 minutes of inactivity**. The first request after sleep takes ~30s to wake.
- No persistent disk on the free plan. SQLite lives at `/tmp/app.db` and **resets on every restart** — uploaded docs and history disappear when the service sleeps and wakes.
- 512 MB RAM, single instance.

If you need persistence, either upgrade the Render plan (then move `DATABASE_PATH` back to a mounted disk path) or swap SQLite for a managed Postgres.

### 3. Enable GitHub Pages

1. In your repo on GitHub, go to **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `main`, folder: `/docs`.
4. Save. The site is published at `https://<yourname>.github.io/ai-document-analyst/` within a minute or two.

### 4. Point the frontend at the backend

Open your GH Pages URL. The provider banner will say "Backend unreachable" and the **Settings** panel will auto-open. Paste your Render URL (e.g. `https://ai-doc-analyst.onrender.com`) and click **Save**. The value is persisted to `localStorage`, so it only has to be entered once per browser.

You can also bake a default backend URL into the page at deploy time by adding the following before the `<script src="./app.js">` tag in `docs/index.html`:

```html
<script>window.AIDA_BACKEND = "https://ai-doc-analyst.onrender.com";</script>
```

## Configuration

| Env var             | Default               | Notes                                          |
| ------------------- | --------------------- | ---------------------------------------------- |
| `LLM_PROVIDER`      | `claude`              | `claude` or `gemini`                           |
| `ANTHROPIC_API_KEY` | (required for Claude) | Your Anthropic API key                         |
| `GEMINI_API_KEY`    | (required for Gemini) | Your Google AI Studio key                      |
| `GEMINI_MODEL`      | `gemini-2.0-flash`    | Override to `gemini-1.5-pro` if you prefer it  |
| `CORS_ORIGINS`      | (empty)               | Comma-separated extra origins. `*.github.io` is allowed by default. |
| `DATABASE_PATH`     | `./data/app.db`       | SQLite file path (relative paths resolve to project root) |
| `MAX_UPLOAD_MB`     | `20`                  | Reject uploads larger than this                |

## API

| Method | Path                          | Body / params                                    | Returns                  |
| ------ | ----------------------------- | ------------------------------------------------ | ------------------------ |
| GET    | `/health`                     |                                                  | `{status, provider}`     |
| GET    | `/provider`                   |                                                  | `ProviderInfo`           |
| POST   | `/upload`                     | multipart `file`                                 | `{document, preview}`    |
| GET    | `/documents`                  |                                                  | `DocumentMeta[]`         |
| GET    | `/summary/{doc_id}`           | optional `?refresh=true`                         | `Summary` (cached)       |
| GET    | `/requirements/{doc_id}`      | optional `?refresh=true`                         | `RequirementsExtraction` |
| POST   | `/qa`                         | `{doc_id, question}`                             | `Answer` with citations  |
| POST   | `/compare`                    | `{doc_id_before, doc_id_after}`                  | `ChangeImpact`           |
| GET    | `/history`                    | optional `?doc_id=N&limit=100`                   | recent queries           |

Interactive docs at `/docs` on the backend.

### GET vs. POST on summary / requirements

`/summary/{doc_id}` and `/requirements/{doc_id}` are `GET`s and stay idempotent by **lazily caching** their results: the first call runs the model and stores the response in the `queries` table; subsequent calls return the stored response. Pass `?refresh=true` to force a re-run.

## Security notes

- **Never commit API keys.** `.env` is gitignored; on Render, keys go in the dashboard with `sync: false`.
- **Don't put a "fallback" API key in the static frontend.** Anything shipped to GitHub Pages is publicly readable — bots actively scrape repos and CDNs for exposed keys.
- If you accidentally leak a key (PR, chat, screenshot), rotate it immediately at the provider's console. The old key is compromised forever.

## Notes

- For Claude, document text is cached server-side via `cache_control: ephemeral`. Repeated calls against the same doc only pay the prefix cost once per 5-minute window.
- For Gemini, structured outputs use `response_mime_type=application/json` + `response_schema=<PydanticModel>`.
- Documents over ~200K characters are truncated before being sent to the model (cap in `app/providers/base.py:MAX_DOC_CHARS`).
- Structured outputs are enforced via Pydantic validation on every response. Responses that don't validate raise a 502.
