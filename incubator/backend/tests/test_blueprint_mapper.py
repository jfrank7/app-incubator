import pytest

from app.schemas.form import EntitySpec, ProductSpec, ScreenSpec
from app.services.blueprint_mapper import BlueprintMapper


@pytest.fixture
def caffeine_spec() -> ProductSpec:
    return ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track caffeine",
        target_user="adults",
        screens=[
            ScreenSpec(name="Dashboard", route="/", description="main"),
            ScreenSpec(name="Add Entry", route="/new", description="log"),
        ],
        features=["logging", "history"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )


def test_mapper_includes_dashboard_module(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "dashboard" in blueprint.selected_modules


def test_mapper_auth_module_when_auth_required(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "auth" in blueprint.selected_modules


def test_mapper_no_auth_module_when_auth_not_required(caffeine_spec):
    caffeine_spec.auth_required = False
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "auth" not in blueprint.selected_modules


def test_mapper_includes_payments_when_spec_says_so(caffeine_spec):
    caffeine_spec.payments_placeholder = True
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" in blueprint.selected_modules


def test_mapper_excludes_payments_by_default(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" not in blueprint.selected_modules


def test_mapper_full_file_plan_has_mobile_and_backend(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    paths = [f.path for f in blueprint.file_plan]
    assert any("package.json" in p for p in paths)
    assert any("main.py" in p for p in paths)


def test_mapper_shell_file_plan_has_only_mobile(caffeine_spec):
    mapper = BlueprintMapper()
    shell_plan = mapper.shell_file_plan(caffeine_spec)
    paths = [f.path for f in shell_plan]
    assert any("package.json" in p for p in paths)
    assert not any("main.py" in p for p in paths)


def test_mapper_includes_env_vars(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    keys = [e.key for e in blueprint.env_vars]
    assert "SECRET_KEY" in keys
    assert "DATABASE_URL" in keys
