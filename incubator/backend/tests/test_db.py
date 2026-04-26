import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session, init_db
from app.db.models import Run


@pytest.mark.asyncio
async def test_create_and_fetch_run(db_session: AsyncSession):
    run = Run(
        id="test-run-123",
        raw_idea="track caffeine",
        status="pending",
        app_name=None,
        form_answers_json="{}",
        product_spec_json=None,
        blueprint_json=None,
        qa_report_json=None,
        error_summary=None,
    )
    db_session.add(run)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == "test-run-123"))
    fetched = result.scalar_one()
    assert fetched.raw_idea == "track caffeine"
    assert fetched.status == "pending"
