from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.stages import run_blueprint_generation, run_spec_generation
from app.schemas.form import FormAnswers


def make_form() -> FormAnswers:
    return FormAnswers(
        app_goal="track caffeine",
        target_user="adults",
        top_3_actions=["log drink", "view total", "set goal"],
        must_have_screens=["dashboard", "add entry"],
        works_offline=True,
        needs_notifications=False,
        core_data_entities=["CaffeineEntry"],
        style_notes="minimal",
        constraints_non_goals="no social",
    )


@pytest.mark.asyncio
async def test_spec_generation_saves_spec_to_db(db_session):
    import json
    import uuid

    from app.db.models import Run
    run_id = str(uuid.uuid4())
    form = make_form()
    run = Run(
        id=run_id,
        raw_idea="caffeine tracker",
        status="pending",
        form_answers_json=form.model_dump_json(),
    )
    db_session.add(run)
    await db_session.commit()

    mock_spec = {
        "app_name": "Caffeine Tracker",
        "app_slug": "caffeine-tracker",
        "goal": "track caffeine",
        "target_user": "adults",
        "screens": [{"name": "Dashboard", "route": "/", "description": "main"}],
        "features": ["logging"],
        "data_entities": [{"name": "CaffeineEntry", "fields": ["id", "mg", "timestamp"]}],
        "offline_support": True,
        "notifications": False,
        "auth_required": True,
        "payments_placeholder": False,
        "style_notes": "minimal",
        "non_goals": ["social"],
    }

    with patch("app.pipeline.stages.claude.generate_json", AsyncMock(return_value=mock_spec)):
        with patch("app.pipeline.stages.sse_manager.emit", AsyncMock()):
            with patch("app.pipeline.stages.sse_manager.emit_done", AsyncMock()):
                await run_spec_generation(run_id, "caffeine tracker", form)

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == run_id))
    updated = result.scalar_one()
    assert updated.status == "awaiting_spec_review"
    assert updated.product_spec_json is not None
    spec_data = json.loads(updated.product_spec_json)
    assert spec_data["app_name"] == "Caffeine Tracker"


@pytest.mark.asyncio
async def test_blueprint_generation_saves_blueprint(db_session):
    import uuid

    from app.db.models import Run
    from app.schemas.form import EntitySpec, ProductSpec, ScreenSpec
    run_id = str(uuid.uuid4())
    spec = ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track caffeine",
        target_user="adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main")],
        features=["logging"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )
    run = Run(
        id=run_id,
        raw_idea="caffeine tracker",
        status="awaiting_spec_review",
        form_answers_json="{}",
        product_spec_json=spec.model_dump_json(),
    )
    db_session.add(run)
    await db_session.commit()

    with patch("app.pipeline.stages.sse_manager.emit", AsyncMock()):
        with patch("app.pipeline.stages.sse_manager.emit_done", AsyncMock()):
            await run_blueprint_generation(run_id, spec)

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == run_id))
    updated = result.scalar_one()
    assert updated.status == "awaiting_blueprint_review"
    assert updated.blueprint_json is not None
