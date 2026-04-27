import shutil
from pathlib import Path

import pytest

from app.schemas.form import (
    ArchitectureBlueprint,
    EntitySpec,
    EnvVar,
    FilePlan,
    ProductSpec,
    ScreenSpec,
)
from app.services.scaffolder import ScaffolderService
from app.templates.modules.manifest import get_module_templates


def test_auth_module_always_present():
    templates = get_module_templates(["auth"])
    assert any("auth" in t for t in templates)


def test_payments_placeholder_module():
    templates = get_module_templates(["payments_placeholder"])
    assert any("paywall" in t for t in templates)


def test_unknown_module_raises():
    with pytest.raises(ValueError, match="Unknown module"):
        get_module_templates(["nonexistent_module"])


@pytest.fixture
def sample_spec() -> ProductSpec:
    return ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track daily caffeine",
        target_user="health-conscious adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main view")],
        features=["logging"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )


@pytest.fixture
def sample_blueprint() -> ArchitectureBlueprint:
    return ArchitectureBlueprint(
        selected_modules=["auth", "dashboard", "local_persistence", "analytics_hook"],
        file_plan=[
            FilePlan(
                path="apps/mobile/package.json",
                template="mobile/base/package.json.j2",
                context_keys=["app_name", "app_slug"],
            ),
            FilePlan(
                path="apps/mobile/app.json",
                template="mobile/base/app.json.j2",
                context_keys=["app_name", "app_slug"],
            ),
        ],
        api_routes=[],
        db_entities=["User"],
        env_vars=[EnvVar(key="SECRET_KEY", example_value="change-me", description="JWT secret")],
    )


@pytest.fixture
def output_dir(tmp_path) -> Path:
    d = tmp_path / "test-run-id"
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_scaffolder_renders_package_json(sample_spec, sample_blueprint, output_dir):
    svc = ScaffolderService()
    svc.scaffold(sample_spec, sample_blueprint, output_dir)
    pkg_path = output_dir / "apps/mobile/package.json"
    assert pkg_path.exists()
    content = pkg_path.read_text()
    assert "caffeine-tracker" in content


def test_scaffolder_renders_app_json_with_app_name(sample_spec, sample_blueprint, output_dir):
    svc = ScaffolderService()
    svc.scaffold(sample_spec, sample_blueprint, output_dir)
    app_json_path = output_dir / "apps/mobile/app.json"
    assert app_json_path.exists()
    content = app_json_path.read_text()
    assert "Caffeine Tracker" in content


def test_scaffolder_returns_file_list(sample_spec, sample_blueprint, output_dir):
    svc = ScaffolderService()
    written = svc.scaffold(sample_spec, sample_blueprint, output_dir)
    assert len(written) == 2
    assert all(isinstance(p, str) for p in written)
