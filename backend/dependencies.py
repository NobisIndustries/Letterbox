from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend import database


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with database.async_session() as session:
        async with session.begin():
            yield session
