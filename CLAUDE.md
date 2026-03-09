# Letter Scanner

## Motivation
Physical letters pile up and are hard to find later. This app lets you photograph letters, automatically clean them up, extract text + metadata via LLM, and store them as searchable PDFs.

## How it works
1. **Capture** — Upload or photograph letter pages
2. **DocRes** — Dewarp + enhance images (Restormer model + OpenCV)
3. **LLM OCR** — Gemini Flash via OpenRouter extracts full text, metadata, and action items
4. **Store** — Save as PDF, index in SQLite with FTS5 full-text search

## Tech stack
- **UI**: Streamlit (3 pages: Ingest, Archive, Tasks)
- **Image processing**: DocRes (local inference, `docres_inference/`)
- **OCR + metadata**: OpenRouter API (`google/gemini-3-flash-preview`)
- **DB**: SQLite + SQLAlchemy + Alembic migrations + FTS5
- **PDF**: img2pdf

## Project structure
- `app.py` — Streamlit entry point
- `db.py` — Database CRUD + FTS5 search
- `models.py` — SQLAlchemy ORM models (Letter, Task)
- `processing.py` — DocRes image processing wrapper
- `llm.py` — OpenRouter API integration
- `pdf_utils.py` — Image-to-PDF conversion
- `alembic/` — Database migrations
- `docres_inference/` — Copied from DocRes repo (don't edit directly)
- `models/` — DocRes weights (docres.pkl, mbd.pkl) — gitignored
- `data/` — SQLite DB + stored PDFs — gitignored

## Running
```
cp .env.example .env  # add OPENROUTER_API_KEY
pip install -r requirements.txt
alembic upgrade head
streamlit run app.py
```

## Conventions
- Absolute imports (not relative) — modules run from `letter_scanner/` directory
- Alembic for all schema changes — never modify tables manually
- Raw LLM responses stored in `raw_llm_response` column for debugging
