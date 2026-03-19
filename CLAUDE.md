# Letter Scanner

## Motivation
Physical letters pile up and are hard to find later. This app lets you photograph letters, automatically clean them up, extract text + metadata via LLM, and store them as searchable PDFs.

## How it works
1. **Capture** — Upload or photograph letter pages (mobile-friendly camera capture)
2. **DocRes** — Dewarp + enhance images (Restormer model + OpenCV)
3. **LLM OCR** — Gemini Flash via OpenRouter extracts full text, metadata, tags, and action items
4. **Store** — Save as compressed PDF, index in SQLite with FTS5 full-text search

## Tech stack
- **Backend**: FastAPI (async, single uvicorn worker)
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Image processing**: DocRes (local inference, `backend/docres_inference/`)
- **OCR + metadata**: OpenRouter API (`google/gemini-3-flash-preview`)
- **DB**: SQLite + async SQLAlchemy + aiosqlite + Alembic migrations + FTS5
- **PDF**: Pillow (compress) + img2pdf
- **Deployment**: Single Docker container, frontend served by FastAPI

## Project structure
- `backend/main.py` — FastAPI app, lifespan, static mount
- `backend/config.py` — pydantic-settings configuration
- `backend/database.py` — async SQLAlchemy engine + session + migrations
- `backend/models.py` — SQLAlchemy ORM models (Letter, Task, Setting)
- `backend/schemas.py` — Pydantic request/response models
- `backend/dependencies.py` — FastAPI dependency injection (get_db)
- `backend/queue.py` — Single-worker asyncio.Queue + in-memory job status store
- `backend/routes/` — API route modules (letters, tasks, settings, senders)
- `backend/services/` — Business logic (ingest pipeline, LLM, processing, PDF)
- `backend/docres_inference/` — Copied from DocRes repo (don't edit directly)
- `frontend/` — React SPA (Vite + TypeScript + Tailwind + shadcn/ui)
- `alembic_migrations/` — Database migrations
- `models/` — DocRes weights (docres.pkl, mbd.pkl) — gitignored
- `data/` — SQLite DB + stored PDFs — gitignored

## Running (development)
```
cp .env.example .env  # add OPENROUTER_API_KEY
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload --port 8000
```

## Running (Docker)
```
cp .env.example .env  # add OPENROUTER_API_KEY
docker compose up --build
```

## API endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/letters/ingest` | Upload images → returns job_id |
| GET | `/api/letters/ingest/jobs` | Poll recent job statuses (last 15min) |
| DELETE | `/api/letters/ingest/jobs` | Clear finished/errored/skipped jobs |
| POST | `/api/letters/ingest/{job_id}/force` | Force-ingest a skipped duplicate |
| GET | `/api/letters` | List/search (q, date_from, date_to, offset, limit, order) |
| GET | `/api/letters/{id}` | Letter detail |
| PATCH | `/api/letters/{id}` | Edit metadata/tags |
| DELETE | `/api/letters/{id}` | Delete letter + PDF |
| GET | `/api/letters/{id}/pdf` | Serve PDF file |
| GET | `/api/tasks` | List tasks (filter: pending/done/all) |
| PATCH | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |
| GET | `/api/settings/{key}` | Get recipients or tags list |
| PUT | `/api/settings/{key}` | Update recipients or tags |
| GET | `/api/senders` | Autocomplete distinct senders |

## Conventions
- Absolute imports from `backend` package (e.g., `from backend.models import Letter`)
- Alembic for all schema changes — never modify tables manually
- Raw LLM responses stored in `raw_llm_response` column for debugging
- Single uvicorn worker to match single-worker queue and avoid SQLite write contention
- Frontend builds to `frontend/dist/`, served as static files by FastAPI
