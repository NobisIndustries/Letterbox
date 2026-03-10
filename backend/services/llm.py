import base64
import json

import httpx

from backend.config import settings

SYSTEM_PROMPT_BASE = """\
You are a document analysis assistant. You receive scanned letter images and extract structured metadata.

Respond with ONLY a valid JSON object (no markdown, no code fences) with these fields:
{
  "title": "short descriptive title",
  "summary": "1-3 sentence summary",
  "full_text": "complete OCR transcription of the letter",
  "sender": "name/organization that sent the letter",
  "receiver": "name/organization the letter is addressed to",
  "creation_date": "YYYY-MM-DD or null if not found",
  "keywords": ["keyword1", "keyword2", ...],
  "tags": ["tag1", "tag2", ...],
  "tasks": [
    {"description": "action item from the letter", "deadline": "YYYY-MM-DD or null"}
  ]
}

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
        prompt += f"\n- For receiver, prefer matching one of these known recipients: {names}"
    if tags:
        tag_list = ", ".join(tags)
        prompt += f"\n- For tags, classify using these known tags where applicable: {tag_list}. You may also add new tags if none fit."
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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()

    raw_text = resp.json()["choices"][0]["message"]["content"]

    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    parsed = json.loads(text)

    # Normalize keywords from list to comma-separated string
    if isinstance(parsed.get("keywords"), list):
        parsed["keywords"] = ", ".join(parsed["keywords"])

    # Normalize tags from list to comma-separated string
    if isinstance(parsed.get("tags"), list):
        parsed["tags"] = ", ".join(parsed["tags"])

    parsed["raw_llm_response"] = raw_text
    return parsed
