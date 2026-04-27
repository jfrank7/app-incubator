from pathlib import Path

TEMPLATES_ROOT = Path(__file__).parent.parent

MODULE_MANIFEST: dict[str, list[str]] = {
    "auth": [
        "mobile/base/app/(auth)/login.tsx.j2",
        "mobile/base/app/(auth)/signup.tsx.j2",
        "backend/base/app/auth/router.py.j2",
        "backend/base/app/auth/service.py.j2",
        "backend/base/app/schemas/auth.py.j2",
        "backend/base/app/core/security.py.j2",
        "backend/base/app/models/user.py.j2",
    ],
    "dashboard": [
        "mobile/base/app/(tabs)/index.tsx.j2",
        "mobile/base/app/(tabs)/_layout.tsx.j2",
    ],
    "settings": [
        "mobile/modules/settings/app/(tabs)/settings.tsx.j2",
    ],
    "list_detail_crud": [
        "mobile/modules/list_detail/app/(tabs)/list.tsx.j2",
        "mobile/modules/list_detail/app/(tabs)/detail.tsx.j2",
        "backend/modules/list_detail/app/api/items.py.j2",
        "backend/modules/list_detail/app/models/item.py.j2",
    ],
    "form_flow": [
        "mobile/modules/form_flow/app/(tabs)/new-entry.tsx.j2",
    ],
    "local_persistence": [
        "mobile/base/lib/db/local.ts.j2",
    ],
    "notifications_placeholder": [
        "mobile/modules/notifications/lib/notifications.ts.j2",
    ],
    "payments_placeholder": [
        "mobile/modules/payments_placeholder/app/paywall.tsx.j2",
        "backend/modules/payments_placeholder/app/api/billing.py.j2",
        "backend/modules/payments_placeholder/app/services/billing.py.j2",
    ],
    "analytics_hook": [
        "mobile/base/lib/telemetry/analytics.ts.j2",
    ],
    "onboarding": [
        "mobile/modules/onboarding/app/onboarding.tsx.j2",
    ],
    "profile": [
        "mobile/modules/profile/app/(tabs)/profile.tsx.j2",
    ],
    "search_filter": [
        "mobile/modules/search/app/(tabs)/search.tsx.j2",
    ],
}

BASE_TEMPLATES: list[str] = [
    "mobile/base/app/_layout.tsx.j2",
    "mobile/base/lib/api/client.ts.j2",
    "mobile/base/lib/storage/session.ts.j2",
    "mobile/base/package.json.j2",
    "mobile/base/app.json.j2",
    "mobile/base/tsconfig.json.j2",
    "backend/base/app/main.py.j2",
    "backend/base/app/db/database.py.j2",
    "backend/base/pyproject.toml.j2",
    "backend/base/.env.example.j2",
    "backend/base/README.md.j2",
]


def get_module_templates(modules: list[str]) -> list[str]:
    unknown = [m for m in modules if m not in MODULE_MANIFEST]
    if unknown:
        raise ValueError(f"Unknown module: {unknown}")
    result: list[str] = []
    for m in modules:
        result.extend(MODULE_MANIFEST[m])
    return list(dict.fromkeys(result))
