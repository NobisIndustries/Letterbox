from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models import Letter

router = APIRouter(tags=["senders"])


@router.get("/api/senders", response_model=list[str])
async def list_senders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Letter.sender)
        .where(Letter.sender.isnot(None))
        .distinct()
        .order_by(Letter.sender)
    )
    return [row[0] for row in result.all()]


@router.get("/api/receivers", response_model=list[str])
async def list_receivers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Letter.receiver)
        .where(Letter.receiver.isnot(None))
        .distinct()
        .order_by(Letter.receiver)
    )
    return [row[0] for row in result.all()]
