import json
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Letter, Setting, Task
from backend.services import llm, processing
from backend.services.pdf import create_pdf


async def _load_setting(session: AsyncSession, key: str) -> list[str]:
    result = await session.execute(
        text("SELECT value FROM settings WHERE key = :key"), {"key": key}
    )
    row = result.first()
    if row:
        return json.loads(row[0])
    return []


async def run_ingest(
    session: AsyncSession,
    images: list[bytes],
    on_progress=None,
) -> Letter:
    async def report(step: str):
        if on_progress:
            await on_progress(step)

    await report("enhancing")
    processed = await processing.process_images(images)

    await report("extracting")
    recipients = await _load_setting(session, "recipients")
    tags = await _load_setting(session, "tags")
    metadata = await llm.extract_metadata(processed, recipients=recipients, tags=tags)

    await report("saving")
    pdf_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = str(settings.pdf_dir / pdf_filename)
    create_pdf(processed, pdf_path)

    creation_date = None
    if metadata.get("creation_date"):
        try:
            creation_date = date.fromisoformat(metadata["creation_date"])
        except (ValueError, TypeError):
            pass

    letter = Letter(
        title=metadata.get("title"),
        summary=metadata.get("summary"),
        sender=metadata.get("sender"),
        receiver=metadata.get("receiver"),
        creation_date=creation_date,
        keywords=metadata.get("keywords"),
        tags=metadata.get("tags"),
        full_text=metadata.get("full_text"),
        pdf_path=f"pdfs/{pdf_filename}",
        page_count=len(images),
        raw_llm_response=metadata.get("raw_llm_response"),
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
    await report("done")
    return letter
