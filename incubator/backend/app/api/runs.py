import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Run
from app.schemas.run import CreateRunRequest, RunListItem, RunResponse

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(body: CreateRunRequest, session: AsyncSession = Depends(get_session)):
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    run = Run(
        id=run_id,
        raw_idea=body.raw_idea,
        status="pending",
        app_name=None,
        form_answers_json=body.form_answers.model_dump_json(),
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


@router.get("", response_model=list[RunListItem])
async def list_runs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).order_by(Run.created_at.desc()))
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
