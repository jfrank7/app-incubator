import pytest

from app.templates.modules.manifest import MODULE_MANIFEST, get_module_templates


def test_auth_module_always_present():
    templates = get_module_templates(["auth"])
    assert any("auth" in t for t in templates)


def test_payments_placeholder_module():
    templates = get_module_templates(["payments_placeholder"])
    assert any("paywall" in t for t in templates)


def test_unknown_module_raises():
    with pytest.raises(ValueError, match="Unknown module"):
        get_module_templates(["nonexistent_module"])
