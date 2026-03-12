import asyncio
import json
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.dependencies import get_db
from backend.models import Letter
from backend.queue import enqueue, enqueue_pdf, force_ingest, get_job
from backend.schemas import (
    IngestResponse,
    LetterListOut,
    LetterListResponse,
    LetterOut,
    LetterUpdate,
)

router = APIRouter(prefix="/api/letters", tags=["letters"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_upload(files: list[UploadFile]):
    if not files:
        raise HTTPException(400, "No files uploaded")
    content_types = [f.content_type for f in files]
    pdf_count = sum(1 for ct in content_types if ct == "application/pdf")
    if pdf_count > 0 and pdf_count < len(files):
        raise HTTPException(400, "Cannot mix PDF and image uploads")
    if pdf_count > 1:
        raise HTTPException(400, "Only one PDF can be uploaded at a time")
    raw_bytes = [await f.read() for f in files]
    if pdf_count == 1:
        job_id = await enqueue_pdf(raw_bytes[0])
    else:
        job_id = await enqueue(raw_bytes)
    return IngestResponse(job_id=job_id)


@router.get("/ingest/{job_id}/status")
async def ingest_status(job_id: str):
    async def event_stream():
        prev_status = None
        while True:
            job = get_job(job_id)
            if job is None:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                return
            if job["status"] != prev_status:
                prev_status = job["status"]
                payload = {
                    "status": job["status"],
                    "letter_id": job.get("letter_id"),
                    "error": job.get("error"),
                    "duplicate_of": job.get("duplicate_of"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if job["status"] in ("done", "error", "skipped"):
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/ingest/{job_id}/force", response_model=IngestResponse)
async def force_ingest_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job["status"] != "skipped":
        raise HTTPException(404, "Job is not in skipped state")
    try:
        new_job_id = await force_ingest(job_id)
    except KeyError:
        raise HTTPException(410, "Cached data no longer available — please re-upload")
    except ValueError:
        raise HTTPException(410, "Cached data expired — please re-upload")
    return IngestResponse(job_id=new_job_id)


def _fts_query(q: str) -> str:
    """Convert a plain search string to an FTS5 prefix query."""
    # Tokenize on whitespace, strip FTS5 special chars, add prefix wildcard
    tokens = q.split()
    safe_tokens = [re.sub(r'[^a-zA-Z0-9äöüÄÖÜß]', '', t) for t in tokens]
    safe_tokens = [t for t in safe_tokens if t]
    if not safe_tokens:
        return ""
    return " ".join(f'"{t}"*' for t in safe_tokens)


@router.get("", response_model=LetterListResponse)
async def list_letters(
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tag: str | None = None,
    receiver: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    order: str = "creation_date",
    db: AsyncSession = Depends(get_db),
):
    if q:
        fts_q = _fts_query(q)
        if not fts_q:
            return LetterListResponse(items=[], total=0)
        # FTS5 prefix search
        fts_result = await db.execute(
            text("SELECT rowid FROM letters_fts WHERE letters_fts MATCH :query ORDER BY rank"),
            {"query": fts_q},
        )
        ids = [row[0] for row in fts_result]
        if not ids:
            return LetterListResponse(items=[], total=0)
        stmt = select(Letter).where(Letter.id.in_(ids))
    else:
        stmt = select(Letter)

    if date_from:
        stmt = stmt.where(Letter.creation_date >= date_from)
    if date_to:
        stmt = stmt.where(Letter.creation_date <= date_to)
    if tag:
        # tags stored as comma-separated string like "tag1, tag2"
        stmt = stmt.where(Letter.tags.contains(tag))
    if receiver:
        stmt = stmt.where(Letter.receiver == receiver)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = count_result.scalar() or 0

    # Order and paginate
    col = getattr(Letter, order, Letter.creation_date)
    stmt = stmt.order_by(col.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    letters = result.scalars().all()

    return LetterListResponse(
        items=[LetterListOut.model_validate(l) for l in letters],
        total=total,
    )


@router.get("/{letter_id}", response_model=LetterOut)
async def get_letter(letter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Letter).options(selectinload(Letter.tasks)).where(Letter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(404, "Letter not found")
    return LetterOut.model_validate(letter)


@router.patch("/{letter_id}", response_model=LetterOut)
async def update_letter(
    letter_id: int, update: LetterUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Letter).options(selectinload(Letter.tasks)).where(Letter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(404, "Letter not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(letter, field, value)
    await db.flush()
    return LetterOut.model_validate(letter)


@router.delete("/{letter_id}", status_code=204)
async def delete_letter(letter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Letter).where(Letter.id == letter_id))
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(404, "Letter not found")
    # Delete PDF file
    if letter.pdf_path:
        pdf_file = settings.data_dir / letter.pdf_path
        if pdf_file.exists():
            pdf_file.unlink()
    await db.delete(letter)


@router.get("/{letter_id}/pdf")
async def get_pdf(letter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Letter).where(Letter.id == letter_id))
    letter = result.scalar_one_or_none()
    if not letter or not letter.pdf_path:
        raise HTTPException(404, "PDF not found")
    pdf_file = settings.data_dir / letter.pdf_path
    if not pdf_file.exists():
        raise HTTPException(404, "PDF file missing")
    return FileResponse(str(pdf_file), media_type="application/pdf")
