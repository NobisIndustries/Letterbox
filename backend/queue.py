import asyncio
import logging
import uuid

from backend.database import async_session
from backend.services.ingest import run_ingest

logger = logging.getLogger(__name__)

_queue: asyncio.Queue | None = None
_jobs: dict[str, dict] = {}


def _get_queue() -> asyncio.Queue:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


async def enqueue(images: list[bytes]) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "letter_id": None, "error": None}
    await _get_queue().put((job_id, images))
    return job_id


async def worker():
    q = _get_queue()
    while True:
        job_id, images = await q.get()
        try:
            _jobs[job_id]["status"] = "processing"

            async def on_progress(step: str):
                _jobs[job_id]["status"] = step

            async with async_session() as session:
                async with session.begin():
                    letter = await run_ingest(session, images, on_progress=on_progress)
                    _jobs[job_id]["letter_id"] = letter.id

            _jobs[job_id]["status"] = "done"
        except Exception:
            logger.exception("Ingest job %s failed", job_id)
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = "Processing failed"
        finally:
            q.task_done()
