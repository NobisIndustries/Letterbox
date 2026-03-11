# ✉️ Letterbox

A personal tool for digitizing physical letters. Photograph a letter, and Letterbox cleans it up, extracts text and metadata, detects todos with deadlines, stores everything as a searchable PDF, and lets you translate any letter on demand.

Built for personal use on a home network. Not production software.

## What it does

1. **Capture** — Upload photos of letter pages from your phone or desktop
2. **Enhance** — Dewarp and clean up the images using [DocRes](https://github.com/ZZZHANG-jx/DocRes) (local ML inference)
3. **Extract** — Send images to Gemini Flash (via OpenRouter) to pull out full text, sender, date, tags, and todos
4. **Store** — Save as a compressed PDF, indexed in SQLite with full-text search
5. **Translate** — Pick a language on any letter to get an on-demand LLM translation

## Limitations

**No authentication.** Anyone who can reach the server can read, edit, and delete your letters. Your letters likely contain sensitive personal and financial information. Do not expose this to the internet. Run it on your local network only, behind a VPN if you need remote access.

**No backups.** The database and PDFs live in `./data/` on the host. If that directory is lost, your archive is gone. You are responsible for backing it up. There is no built-in backup feature yet.

**Single user.** No concept of users or permissions. Designed for one person.

**Slow on CPU.** The DocRes dewarping model runs on CPU in the container (no GPU). Expect 10–30 seconds per image depending on your hardware.

**LLM extraction is imperfect.** Dates, senders, and tags are extracted by a language model and will occasionally be wrong.
## Requirements

- Docker + Docker Compose
- An [OpenRouter](https://openrouter.ai) API key (Gemini Flash is cheap — a few fractions of a cent per letter)
- ~1Gb disk for the ML models (downloaded automatically on first run) + disk space for letter pdfs

## Setup

### Option A: Prebuilt image (recommended)

```bash
# Create a directory for your data
mkdir letterbox && cd letterbox

# Create .env with your API key
echo "OPENROUTER_API_KEY=your-key-here" > .env

# Download the compose file
curl -O https://raw.githubusercontent.com/nobisindustries/letterbox/main/docker-compose.yml

docker compose up
```

### Option B: Build from source

```bash
git clone https://github.com/nobisindustries/letterbox
cd letterbox
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
docker compose up --build
```

Open `http://localhost:8000` in your browser.

On first start, the two ML model weights (~1Gb total) are downloaded from Hugging Face into `./models/`. Subsequent starts skip the download.

## Data

Everything lives outside the container:

- `./data/letters.db` — SQLite database
- `./data/pdfs/` — generated PDFs
- `./models/` — ML model weights

Back up `./data/` regularly. The models can always be re-downloaded.

## Tech stack

- **Backend**: FastAPI + SQLite (async SQLAlchemy + FTS5)
- **Frontend**: React + TypeScript + Tailwind + shadcn/ui
- **Image processing**: DocRes (Restormer model, local inference)
- **OCR/metadata**: OpenRouter API (Gemini 3 Flash)
- **Deployment**: Single Docker container

## Development

```bash
cp .env.example .env
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload --port 8000
```

## License

MIT — see [LICENSE](LICENSE).
