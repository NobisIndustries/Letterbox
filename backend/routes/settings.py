import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models import Setting
from backend.schemas import SettingOut, SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

ALLOWED_KEYS = {"recipients", "tags", "dewarping_method", "translation_languages"}


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
