import pytest
from app.schemas.form import FormAnswers, ProductSpec, ArchitectureBlueprint
from app.schemas.pipeline import RunState, QACheck, QAResults


def test_form_answers_requires_exactly_3_actions():
    with pytest.raises(Exception):
        FormAnswers(
            app_goal="track caffeine",
            target_user="health-conscious adults",
            top_3_actions=["log drink", "view total"],  # only 2
            must_have_screens=["dashboard"],
            works_offline=True,
            needs_notifications=False,
            core_data_entities=["CaffeineEntry"],
            style_notes="clean minimal",
            constraints_non_goals="no social features",
        )


def test_form_answers_valid():
    fa = FormAnswers(
        app_goal="track caffeine",
        target_user="health-conscious adults",
        top_3_actions=["log drink", "view daily total", "set reduction goal"],
        must_have_screens=["dashboard", "add entry", "history"],
        works_offline=True,
        needs_notifications=False,
        core_data_entities=["CaffeineEntry", "DailyGoal"],
        style_notes="clean minimal",
        constraints_non_goals="no social features",
    )
    assert fa.include_payments_placeholder is False
    assert fa.auth_required is True


def test_product_spec_auth_always_true():
    from app.schemas.form import ScreenSpec, EntitySpec
    spec = ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track daily caffeine",
        target_user="health-conscious adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main view")],
        features=["logging", "history"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )
    assert spec.auth_required is True


def test_qa_results_passes_only_when_all_checks_pass():
    results = QAResults(
        passed=True,
        checks=[
            QACheck(name="ruff", passed=True, output="All good", error=None),
            QACheck(name="pytest", passed=True, output="3 passed", error=None),
        ],
        summary="All checks passed",
    )
    assert results.passed is True
