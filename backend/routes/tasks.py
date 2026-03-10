from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.dependencies import get_db
from backend.models import Letter, Task
from backend.schemas import TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    filter: str = Query("all", pattern="^(pending|done|all)$"),
    recipient: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).options(selectinload(Task.letter))
    if filter == "pending":
        stmt = stmt.where(Task.is_done == False)  # noqa: E712
    elif filter == "done":
        stmt = stmt.where(Task.is_done == True)  # noqa: E712
    if recipient:
        stmt = stmt.join(Task.letter).where(Letter.receiver == recipient)
    stmt = stmt.order_by(Task.deadline.asc().nullslast())
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    out = []
    for t in tasks:
        d = TaskOut.model_validate(t)
        d.letter_title = t.letter.title if t.letter else None
        d.letter_sender = t.letter.sender if t.letter else None
        d.letter_receiver = t.letter.receiver if t.letter else None
        out.append(d)
    return out


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, update: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
