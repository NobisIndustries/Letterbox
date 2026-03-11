import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

logging.basicConfig(level=logging.INFO, force=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.database import run_migrations
from backend.queue import worker
from backend.routes import letters, senders, settings, tasks, translations
from backend.services.processing import idle_unloader


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    worker_task = asyncio.create_task(worker())
    unloader_task = asyncio.create_task(idle_unloader())
    yield
    worker_task.cancel()
    unloader_task.cancel()
    for task in (worker_task, unloader_task):
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Letter Scanner", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(letters.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(senders.router)
app.include_router(translations.router)

# Serve frontend static files if built
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
