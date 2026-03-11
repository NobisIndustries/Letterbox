import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models import Letter, LetterTranslation, Setting
from backend.schemas import TranslationOut
from backend.services.llm import translate_letter

router = APIRouter(prefix="/api/letters", tags=["translations"])


@router.get("/{letter_id}/translations/{language}", response_model=TranslationOut)
async def get_translation(
    letter_id: int, language: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(LetterTranslation).where(
            LetterTranslation.letter_id == letter_id,
            LetterTranslation.language == language,
        )
    )
    translation = result.scalar_one_or_none()
    if not translation:
        raise HTTPException(404, "Translation not found")
    return translation


@router.post("/{letter_id}/translations/{language}", response_model=TranslationOut)
async def create_translation(
    letter_id: int, language: str, db: AsyncSession = Depends(get_db)
):
    # Validate language against setting
    setting_result = await db.execute(
        select(Setting).where(Setting.key == "translation_languages")
    )
    setting = setting_result.scalar_one_or_none()
    allowed = json.loads(setting.value) if setting else []
    if language not in allowed:
        raise HTTPException(400, f"Language '{language}' is not in the configured translation languages")

    # Check letter exists and has full_text
    letter_result = await db.execute(select(Letter).where(Letter.id == letter_id))
    letter = letter_result.scalar_one_or_none()
    if not letter:
        raise HTTPException(404, "Letter not found")
    if not letter.full_text:
        raise HTTPException(422, "Letter has no text to translate")

    # Return cached translation if it exists
    existing_result = await db.execute(
        select(LetterTranslation).where(
            LetterTranslation.letter_id == letter_id,
            LetterTranslation.language == language,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    # Call LLM and store result
    data = await translate_letter(letter.full_text, language)
    translation = LetterTranslation(
        letter_id=letter_id,
        language=language,
        translated_text=data.get("translated_text"),
        translated_summary=data.get("translated_summary"),
    )
    db.add(translation)
    await db.flush()
    await db.refresh(translation)
    return translation
