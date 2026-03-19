import asyncio
import logging
import time
import uuid

from backend import database
from backend.services.ingest import (
    enhance_images,
    run_ingest,
    run_ingest_forced_images,
    run_ingest_forced_pdf,
    run_ingest_pdf,
)

logger = logging.getLogger(__name__)

_queue: asyncio.Queue | None = None
_jobs: dict[str, dict] = {}
_JOB_RETENTION = 900  # 15 minutes

# Cache of pending (skipped-duplicate) ingest payloads, keyed by original job_id.
# Each entry: {"kind": "images"|"pdf", "processed": list[bytes]|bytes,
#              "metadata": dict, "expires_at": float}
_pending_cache: dict[str, dict] = {}
_PENDING_TTL = 600  # 10 minutes


def _get_queue() -> asyncio.Queue:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def get_recent_jobs(since_minutes: int = 15) -> dict[str, dict]:
    cutoff = time.time() - since_minutes * 60
    return {jid: job for jid, job in _jobs.items() if job["created_at"] >= cutoff}


def cleanup_old_jobs() -> None:
    cutoff = time.time() - _JOB_RETENTION
    expired = [jid for jid, job in _jobs.items() if job["created_at"] < cutoff]
    for jid in expired:
        del _jobs[jid]


_CLEARABLE = {"done", "error", "skipped"}


def clear_finished_jobs() -> int:
    to_remove = [jid for jid, job in _jobs.items() if job["status"] in _CLEARABLE]
    for jid in to_remove:
        _pending_cache.pop(jid, None)
        del _jobs[jid]
    return len(to_remove)


async def enqueue(images: list[bytes]) -> str:
    cleanup_old_jobs()
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "letter_id": None, "error": None, "duplicate_of": None, "created_at": time.time()}
    await _get_queue().put((job_id, images))
    logger.info("Enqueued image ingest job %s (%d image(s))", job_id, len(images))
    return job_id


async def _finish_ingest(job_id: str, processed: list[bytes]) -> None:
    try:
        async def on_progress(step: str):
            _jobs[job_id]["status"] = step

        async with database.async_session() as session:
            async with session.begin():
                letter, duplicate_of, metadata = await run_ingest(session, processed, on_progress=on_progress)
                if duplicate_of is not None:
                    _jobs[job_id]["duplicate_of"] = duplicate_of
                    _jobs[job_id]["status"] = "skipped"
                    _pending_cache[job_id] = {
                        "kind": "images",
                        "processed": processed,
                        "metadata": metadata,
                        "expires_at": time.monotonic() + _PENDING_TTL,
                    }
                    return
                _jobs[job_id]["letter_id"] = letter.id

        _jobs[job_id]["status"] = "done"
    except Exception as e:
        logger.exception("Ingest job %s failed", job_id)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


async def enqueue_pdf(pdf_bytes: bytes) -> str:
    cleanup_old_jobs()
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "letter_id": None, "error": None, "duplicate_of": None, "created_at": time.time()}
    logger.info("Enqueued PDF ingest job %s (%d bytes)", job_id, len(pdf_bytes))
    task = asyncio.create_task(_finish_ingest_pdf(job_id, pdf_bytes))
    task.add_done_callback(lambda t: logger.error("Unhandled error in PDF ingest task: %s", t.exception()) if not t.cancelled() and t.exception() else None)
    return job_id


async def _finish_ingest_pdf(job_id: str, pdf_bytes: bytes) -> None:
    try:
        async def on_progress(step: str):
            _jobs[job_id]["status"] = step

        async with database.async_session() as session:
            async with session.begin():
                letter, duplicate_of, metadata = await run_ingest_pdf(session, pdf_bytes, on_progress=on_progress)
                if duplicate_of is not None:
                    _jobs[job_id]["duplicate_of"] = duplicate_of
                    _jobs[job_id]["status"] = "skipped"
                    _pending_cache[job_id] = {
                        "kind": "pdf",
                        "processed": pdf_bytes,
                        "metadata": metadata,
                        "expires_at": time.monotonic() + _PENDING_TTL,
                    }
                    return
                _jobs[job_id]["letter_id"] = letter.id

        _jobs[job_id]["status"] = "done"
    except Exception as e:
        logger.exception("PDF ingest job %s failed", job_id)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


async def _finish_force_ingest(job_id: str, processed: list[bytes], metadata: dict) -> None:
    try:
        async def on_progress(step: str):
            _jobs[job_id]["status"] = step

        async with database.async_session() as session:
            async with session.begin():
                letter = await run_ingest_forced_images(session, processed, metadata, on_progress=on_progress)
                _jobs[job_id]["letter_id"] = letter.id

        _jobs[job_id]["status"] = "done"
    except Exception as e:
        logger.exception("Force ingest job %s failed", job_id)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


async def _finish_force_ingest_pdf(job_id: str, pdf_bytes: bytes, metadata: dict) -> None:
    try:
        async def on_progress(step: str):
            _jobs[job_id]["status"] = step

        async with database.async_session() as session:
            async with session.begin():
                letter = await run_ingest_forced_pdf(session, pdf_bytes, metadata, on_progress=on_progress)
                _jobs[job_id]["letter_id"] = letter.id

        _jobs[job_id]["status"] = "done"
    except Exception as e:
        logger.exception("Force PDF ingest job %s failed", job_id)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


async def force_ingest(job_id: str) -> str:
    """Re-use the cached processed data + metadata from a skipped job and save directly.

    Returns the new job_id. Raises KeyError if not cached, ValueError if expired.
    """
    entry = _pending_cache.get(job_id)
    if entry is None:
        raise KeyError(job_id)
    if time.monotonic() > entry["expires_at"]:
        del _pending_cache[job_id]
        raise ValueError("expired")

    new_job_id = str(uuid.uuid4())
    _jobs[new_job_id] = {"status": "saving", "letter_id": None, "error": None, "duplicate_of": None, "created_at": time.time()}

    del _pending_cache[job_id]

    if entry["kind"] == "images":
        task = asyncio.create_task(_finish_force_ingest(new_job_id, entry["processed"], entry["metadata"]))
    else:
        task = asyncio.create_task(_finish_force_ingest_pdf(new_job_id, entry["processed"], entry["metadata"]))

    task.add_done_callback(
        lambda t: logger.error("Unhandled error in force ingest task: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )
    logger.info("Force ingest: original=%s new=%s kind=%s", job_id, new_job_id, entry["kind"])
    return new_job_id


async def worker():
    q = _get_queue()
    while True:
        job_id, images = await q.get()
        logger.info("Worker picked up job %s", job_id)
        try:
            _jobs[job_id]["status"] = "enhancing"
            processed = await enhance_images(images)
        except Exception as e:
            logger.exception("Ingest job %s failed during enhancing", job_id)
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = f"{type(e).__name__}: {e}"
            q.task_done()
            continue

        q.task_done()
        task = asyncio.create_task(_finish_ingest(job_id, processed))
        task.add_done_callback(lambda t: logger.error("Unhandled error in ingest task: %s", t.exception()) if not t.cancelled() and t.exception() else None)
