from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models import Task
from backend.schemas import TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    filter: str = Query("all", regex="^(pending|done|all)$"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task)
    if filter == "pending":
        stmt = stmt.where(Task.is_done == False)  # noqa: E712
    elif filter == "done":
        stmt = stmt.where(Task.is_done == True)  # noqa: E712
    stmt = stmt.order_by(Task.deadline.asc().nullslast())
    result = await db.execute(stmt)
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


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
