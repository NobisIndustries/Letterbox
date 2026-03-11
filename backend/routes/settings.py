import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.dependencies import get_db
from backend.models import Setting
from backend.schemas import SettingOut, SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

ALLOWED_KEYS = {"recipients", "tags", "dewarping_method", "translation_languages"}


@router.get("/openrouter-credits")
async def get_openrouter_credits():
    if not settings.openrouter_api_key:
        raise HTTPException(503, "OpenRouter API key not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            timeout=10,
        )
    if not resp.is_success:
        raise HTTPException(502, "Failed to fetch OpenRouter credits")
    data = resp.json().get("data", {})
    return {
        "label": data.get("label"),
        "limit": data.get("limit"),
        "usage": data.get("usage"),
        "is_free_tier": data.get("is_free_tier"),
    }


@router.get("/{key}", response_model=SettingOut)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    if key not in ALLOWED_KEYS:
        raise HTTPException(404, "Setting not found")
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingOut(key=key, value=[])
    return SettingOut(key=setting.key, value=json.loads(setting.value))


@router.put("/{key}", response_model=SettingOut)
async def update_setting(
    key: str, update: SettingUpdate, db: AsyncSession = Depends(get_db)
):
    if key not in ALLOWED_KEYS:
        raise HTTPException(404, "Setting not found")
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    value_json = json.dumps(update.value)
    if setting:
        setting.value = value_json
    else:
        setting = Setting(key=key, value=value_json)
        db.add(setting)
    await db.flush()
    return SettingOut(key=key, value=update.value)
