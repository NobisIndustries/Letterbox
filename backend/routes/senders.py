from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models import Letter

router = APIRouter(prefix="/api/senders", tags=["senders"])


@router.get("", response_model=list[str])
async def list_senders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Letter.sender)
        .where(Letter.sender.isnot(None))
        .distinct()
        .order_by(Letter.sender)
    )
    return [row[0] for row in result.all()]
