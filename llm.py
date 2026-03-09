import base64
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-3-flash-preview"

SYSTEM_PROMPT = """\
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
  "tasks": [
    {"description": "action item from the letter", "deadline": "YYYY-MM-DD or null"}
  ]
}

Rules:
- Transcribe the full text faithfully, preserving the original language
- Extract ALL action items/deadlines as tasks
- If a field cannot be determined, use null (or empty list for keywords/tasks)
- For creation_date, look for dates printed on the letter
- Keywords should capture the main topics (3-8 keywords)
- All text fields should be in the letter's original language
"""


def extract_metadata(images: list[bytes]) -> dict:
    """Send processed images to OpenRouter and extract structured metadata."""
    content = [{"type": "text", "text": "Extract metadata from this letter:"}]

    for img_bytes in images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "max_tokens": 4096,
        },
        timeout=120,
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

    # Keep raw response for storage
    parsed["raw_llm_response"] = raw_text

    return parsed
