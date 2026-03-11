import json
import uuid
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Letter, Setting, Task
from backend.services import llm, processing
from backend.services.pdf import create_pdf

# SimHash duplicate detection
# We compute a 64-bit SimHash over character trigrams of the full transcript.
# Hamming distance ≤ SIMHASH_THRESHOLD bits indicates a probable duplicate.
SIMHASH_THRESHOLD = 5
SIMHASH_BITS = 64


def _simhash(text_: str) -> int:
    """Compute a 64-bit SimHash over character trigrams of text_."""
    if not text_:
        return 0
    # Build trigrams
    ngrams = [text_[i : i + 3] for i in range(len(text_) - 2)] or [text_]
    v = [0] * SIMHASH_BITS
    for gram in ngrams:
        h = hash(gram) & ((1 << SIMHASH_BITS) - 1)
        for i in range(SIMHASH_BITS):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    result = 0
    for i in range(SIMHASH_BITS):
        if v[i] > 0:
            result |= 1 << i
    return result


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


async def find_duplicate(
    session: AsyncSession,
    full_text: str | None,
    creation_date: date | None,
) -> int | None:
    """Return the letter_id of a probable duplicate, or None.

    Strategy:
    - Pre-filter by creation_date (same date, or both NULL).
    - For NULL creation_date letters the candidate set could grow large over
      time; accepted as a full table scan for now since this is a personal app
      with a small dataset. Revisit if performance becomes an issue.
    - Compare SimHashes with Hamming distance ≤ SIMHASH_THRESHOLD.
    """
    if not full_text:
        return None

    new_hash = _simhash(full_text)

    if creation_date is not None:
        result = await session.execute(
            select(Letter.id, Letter.transcript_simhash).where(
                Letter.creation_date == creation_date,
                Letter.transcript_simhash.is_not(None),
            )
        )
    else:
        result = await session.execute(
            select(Letter.id, Letter.transcript_simhash).where(
                Letter.creation_date.is_(None),
                Letter.transcript_simhash.is_not(None),
            )
        )

    for letter_id, stored_hash in result:
        if _hamming(new_hash, stored_hash) <= SIMHASH_THRESHOLD:
            return letter_id

    return None


async def _load_setting(session: AsyncSession, key: str) -> list[str]:
    result = await session.execute(
        text("SELECT value FROM settings WHERE key = :key"), {"key": key}
    )
    row = result.first()
    if row:
        return json.loads(row[0])
    return []


async def load_dewarping_method(session: AsyncSession) -> str:
    """Load the dewarping method from settings. Returns 'deep_learning' or 'classic'."""
    values = await _load_setting(session, "dewarping_method")
    if values and values[0] in ("classic", "deep_learning"):
        return values[0]
    return "deep_learning"


async def enhance_images(images: list[bytes]) -> list[bytes]:
    from backend import database
    async with database.async_session() as session:
        method = await load_dewarping_method(session)
    return await processing.process_images(images, dewarping_method=method)


async def run_ingest(
    session: AsyncSession,
    processed: list[bytes],
    on_progress=None,
) -> tuple[Letter, int | None]:
    """Run the ingest pipeline for image uploads.

    Returns (letter, duplicate_of_id). If duplicate_of_id is not None the
    letter was not saved and the caller should treat the job as skipped.
    """
    async def report(step: str):
        if on_progress:
            await on_progress(step)

    await report("extracting")
    recipients = await _load_setting(session, "recipients")
    tags = await _load_setting(session, "tags")
    metadata = await llm.extract_metadata(processed, recipients=recipients, tags=tags)

    creation_date = None
    if metadata.get("creation_date"):
        try:
            creation_date = date.fromisoformat(metadata["creation_date"])
        except (ValueError, TypeError):
            pass

    duplicate_of = await find_duplicate(session, metadata.get("full_text"), creation_date)
    if duplicate_of is not None:
        return None, duplicate_of

    await report("saving")
    pdf_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = str(settings.pdf_dir / pdf_filename)
    create_pdf(processed, pdf_path)

    full_text = metadata.get("full_text")
    letter = Letter(
        title=metadata.get("title"),
        summary=metadata.get("summary"),
        sender=metadata.get("sender"),
        receiver=metadata.get("receiver"),
        creation_date=creation_date,
        keywords=metadata.get("keywords"),
        tags=metadata.get("tags"),
        full_text=full_text,
        pdf_path=f"pdfs/{pdf_filename}",
        page_count=len(processed),
        raw_llm_response=metadata.get("raw_llm_response"),
        transcript_simhash=_simhash(full_text) if full_text else None,
    )
    session.add(letter)
    await session.flush()

    for task_data in metadata.get("tasks", []):
        deadline = None
        if task_data.get("deadline"):
            try:
                deadline = date.fromisoformat(task_data["deadline"])
            except (ValueError, TypeError):
                pass
        task = Task(
            letter_id=letter.id,
            description=task_data.get("description", ""),
            deadline=deadline,
        )
        session.add(task)

    await session.flush()
    return letter, None


async def run_ingest_pdf(
    session: AsyncSession,
    pdf_bytes: bytes,
    on_progress=None,
) -> tuple[Letter, int | None]:
    """Run the ingest pipeline for PDF uploads.

    Returns (letter, duplicate_of_id). If duplicate_of_id is not None the
    letter was not saved and the caller should treat the job as skipped.
    """
    async def report(step: str):
        if on_progress:
            await on_progress(step)

    await report("extracting")
    recipients = await _load_setting(session, "recipients")
    tags = await _load_setting(session, "tags")
    metadata = await llm.extract_metadata_from_pdf(pdf_bytes, recipients=recipients, tags=tags)

    creation_date = None
    if metadata.get("creation_date"):
        try:
            creation_date = date.fromisoformat(metadata["creation_date"])
        except (ValueError, TypeError):
            pass

    duplicate_of = await find_duplicate(session, metadata.get("full_text"), creation_date)
    if duplicate_of is not None:
        return None, duplicate_of

    await report("saving")
    pdf_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = settings.pdf_dir / pdf_filename
    pdf_path.write_bytes(pdf_bytes)

    full_text = metadata.get("full_text")
    letter = Letter(
        title=metadata.get("title"),
        summary=metadata.get("summary"),
        sender=metadata.get("sender"),
        receiver=metadata.get("receiver"),
        creation_date=creation_date,
        keywords=metadata.get("keywords"),
        tags=metadata.get("tags"),
        full_text=full_text,
        pdf_path=f"pdfs/{pdf_filename}",
        page_count=1,
        raw_llm_response=metadata.get("raw_llm_response"),
        transcript_simhash=_simhash(full_text) if full_text else None,
    )
    session.add(letter)
    await session.flush()

    for task_data in metadata.get("tasks", []):
        deadline = None
        if task_data.get("deadline"):
            try:
                deadline = date.fromisoformat(task_data["deadline"])
            except (ValueError, TypeError):
                pass
        task = Task(
            letter_id=letter.id,
            description=task_data.get("description", ""),
            deadline=deadline,
        )
        session.add(task)

    await session.flush()
    return letter, None
