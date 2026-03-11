import base64
import json
import logging
from json import JSONDecodeError

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 2

SYSTEM_PROMPT_BASE = """\
You are a document analysis assistant. You receive scanned letter images and extract structured metadata.

Respond with ONLY a valid JSON object (no markdown, no code fences) with these fields, in this exact order:
{
  "title": "short descriptive title",
  "summary": "1-3 sentence summary",
  "sender": "name/organization that sent the letter",
  "receiver": "name/organization the letter is addressed to",
  "creation_date": "YYYY-MM-DD or null if not found",
  "keywords": ["keyword1", "keyword2", ...],
  "tags": ["tag1", "tag2", ...],
  "tasks": [
    {"description": "action item from the letter", "deadline": "YYYY-MM-DD or null"}
  ],
  "full_text": "complete OCR transcription of the letter"
}

IMPORTANT: Output all short metadata fields BEFORE full_text. The full_text field must be last.

Rules:
- Transcribe the full text faithfully, preserving the original language
- Only create tasks for items requiring concrete personal action with real consequences: payment deadlines, legal/contractual deadlines, appointments, required document returns, subscription cancellations before auto-renewal, redeemable coupon codes (include the code in the description), or findings/results that warrant professional follow-up (e.g. abnormal lab values). Do NOT create tasks for: marketing calls-to-action, website links, advisory suggestions, informational notices without deadlines, or anything where inaction has no real consequence. Most letters get 0 tasks. Max 2 tasks total.
- If a field cannot be determined, use null (or empty list for keywords/tasks/tags)
- For creation_date, look for dates printed on the letter
- Keywords should capture the main topics (3-8 keywords)
- All text fields should be in the letter's original language"""


def _build_system_prompt(recipients: list[str], tags: list[str]) -> str:
    prompt = SYSTEM_PROMPT_BASE
    if recipients:
        names = ", ".join(recipients)
        prompt += f"\n- For receiver, prefer matching one of these known recipients: {names}. If none match, still extract the actual recipient from the letter"
    if tags:
        tag_list = ", ".join(tags)
        prompt += f"\n- For tags, classify using these known tags where applicable: {tag_list}"
    return prompt


async def extract_metadata(
    images: list[bytes],
    recipients: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    system_prompt = _build_system_prompt(recipients or [], tags or [])

    content: list[dict] = [{"type": "text", "text": "Extract metadata from this letter:"}]
    for img_bytes in images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": 8192,
    }

    return await _call_llm_with_retry(payload, f"{len(images)} image(s)")


async def _call_llm_with_retry(payload: dict, description: str) -> dict:
    """Call the LLM API with retries on truncated/invalid JSON responses."""
    last_error = None
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        logger.info("Calling LLM (%s) for %s (attempt %d/%d)",
                     settings.llm_model, description, attempt, MAX_LLM_RETRIES)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                settings.openrouter_url,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        finish_reason = data["choices"][0].get("finish_reason", "unknown")
        raw_text = data["choices"][0]["message"]["content"]
        logger.info("LLM response received (status %d, finish_reason=%s, length=%d chars)",
                     resp.status_code, finish_reason, len(raw_text))

        if finish_reason == "length":
            logger.warning("LLM response was truncated (finish_reason=length)")

        try:
            return _parse_llm_response(raw_text)
        except JSONDecodeError as e:
            last_error = e
            logger.warning("LLM returned invalid JSON (attempt %d/%d): %s",
                           attempt, MAX_LLM_RETRIES, e)

    logger.error("LLM failed to return valid JSON after %d attempts", MAX_LLM_RETRIES)
    raise last_error


def _try_repair_truncated_json(text: str) -> dict | None:
    """Attempt to repair JSON truncated mid-string (typically in full_text).

    Handles the common case where the response is cut off inside a string value
    by closing the string and any open structures.
    """
    # Try progressively trimming from the end and closing the JSON
    # The truncation is almost always inside full_text (a long string value)
    for trim in range(0, min(200, len(text)), 1):
        candidate = text if trim == 0 else text[:-trim]
        # Try closing as: unterminated string -> close string, close object
        for suffix in ['"}', '"}]', '"]}', '"]]}']:
            try:
                parsed = json.loads(candidate + suffix)
                if isinstance(parsed, dict) and "title" in parsed:
                    logger.warning("Repaired truncated JSON by appending %r (trimmed %d chars)",
                                   suffix, trim)
                    return parsed
            except JSONDecodeError:
                continue
    return None


def _parse_llm_response(raw_text: str) -> dict:
    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except JSONDecodeError:
        # Attempt to repair truncated JSON before giving up
        repaired = _try_repair_truncated_json(text)
        if repaired is not None:
            repaired["_truncated"] = True
            parsed = repaired
        else:
            logger.error(f"Could not json decode this response: {raw_text}")
            raise

    # Normalize keywords from list to comma-separated string
    if isinstance(parsed.get("keywords"), list):
        parsed["keywords"] = ", ".join(parsed["keywords"])

    # Normalize tags from list to comma-separated string
    if isinstance(parsed.get("tags"), list):
        parsed["tags"] = ", ".join(parsed["tags"])

    parsed["raw_llm_response"] = raw_text
    return parsed


async def extract_metadata_from_pdf(
    pdf_bytes: bytes,
    recipients: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    system_prompt = _build_system_prompt(recipients or [], tags or [])
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    content: list[dict] = [
        {"type": "text", "text": "Extract metadata from this letter:"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:application/pdf;base64,{b64}"},
        },
    ]

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": 8192,
    }

    return await _call_llm_with_retry(payload, "PDF")


TRANSLATE_SYSTEM_PROMPT = """\
You are a translation assistant. You receive the full text of a letter and translate it into the requested language.

Respond with ONLY a valid JSON object (no markdown, no code fences) with these fields:
{
  "translated_text": "complete translation of the letter text",
  "translated_summary": "1-3 sentence summary in the target language"
}"""


async def translate_letter(full_text: str, target_language: str) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            settings.openrouter_url,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Translate the following letter text into {target_language}:\n\n{full_text}",
                    },
                ],
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()

    raw_text = resp.json()["choices"][0]["message"]["content"]

    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)
