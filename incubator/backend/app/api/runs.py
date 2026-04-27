import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Run
from app.schemas.form import ArchitectureBlueprint, ProductSpec
from app.schemas.run import (
    ApproveBlueprintRequest,
    ApproveShellRequest,
    ApproveSpecRequest,
    CreateRunRequest,
    RunListItem,
    RunResponse,
)
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(body: CreateRunRequest, session: AsyncSession = Depends(get_session)):
    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        raw_idea=body.raw_idea,
        status="pending",
        app_name=None,
        form_answers_json=body.form_answers.model_dump_json(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    async def _kick_spec():
        from app.pipeline.stages import run_spec_generation

        await run_spec_generation(run_id, body.raw_idea, body.form_answers)

    asyncio.create_task(_kick_spec())
    return run


@router.post("/{run_id}/approve-spec", response_model=RunResponse)
async def approve_spec(
    run_id: str, body: ApproveSpecRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_spec_review":
        raise HTTPException(
            status_code=409,
            detail=f"Run is in status '{run.status}', expected 'awaiting_spec_review'",
        )

    run.product_spec_json = body.spec.model_dump_json()
    run.app_name = body.spec.app_name
    await session.commit()
    await session.refresh(run)

    async def _kick_blueprint():
        from app.pipeline.stages import run_blueprint_generation

        await run_blueprint_generation(run_id, body.spec)

    asyncio.create_task(_kick_blueprint())
    return run


@router.post("/{run_id}/approve-blueprint", response_model=RunResponse)
async def approve_blueprint(
    run_id: str, body: ApproveBlueprintRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_blueprint_review":
        raise HTTPException(
            status_code=409,
            detail=f"Run is in status '{run.status}', expected 'awaiting_blueprint_review'",
        )
    if not run.product_spec_json:
        raise HTTPException(status_code=422, detail="No product spec found on run")

    run.blueprint_json = body.blueprint.model_dump_json()
    await session.commit()
    await session.refresh(run)

    spec = ProductSpec.model_validate_json(run.product_spec_json)

    async def _kick_shell():
        from app.pipeline.stages import run_shell_scaffolding

        await run_shell_scaffolding(run_id, spec, body.blueprint)

    asyncio.create_task(_kick_shell())
    return run


@router.post("/{run_id}/approve-shell", response_model=RunResponse)
async def approve_shell(
    run_id: str, body: ApproveShellRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_shell_review":
        raise HTTPException(
            status_code=409,
            detail=f"Run is in status '{run.status}', expected 'awaiting_shell_review'",
        )
    if not run.product_spec_json or not run.blueprint_json:
        raise HTTPException(status_code=422, detail="Missing spec or blueprint")

    spec = ProductSpec.model_validate_json(run.product_spec_json)
    blueprint = ArchitectureBlueprint.model_validate_json(run.blueprint_json)

    async def _kick_full():
        from app.pipeline.stages import run_full_scaffolding

        await run_full_scaffolding(run_id, spec, blueprint)

    asyncio.create_task(_kick_full())
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


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    q = sse_manager.subscribe(run_id)

    async def event_generator():
        try:
            while True:
                data = await asyncio.wait_for(q.get(), timeout=30.0)
                if data is None:
                    break
                yield f"data: {data}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'stage': 'heartbeat', 'message': 'ping'})}\n\n"
        finally:
            sse_manager.unsubscribe(run_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{run_id}/artifacts")
async def get_artifacts(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "product_spec": json.loads(run.product_spec_json) if run.product_spec_json else None,
        "blueprint": json.loads(run.blueprint_json) if run.blueprint_json else None,
        "stage_logs": json.loads(run.stage_logs_json) if run.stage_logs_json else [],
    }
