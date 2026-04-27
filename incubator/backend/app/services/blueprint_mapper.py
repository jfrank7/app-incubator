from app.schemas.form import ArchitectureBlueprint, EnvVar, FilePlan, ProductSpec

MOBILE_BASE_FILES: list[tuple[str, str]] = [
    ("apps/mobile/package.json", "mobile/base/package.json.j2"),
    ("apps/mobile/app.json", "mobile/base/app.json.j2"),
    ("apps/mobile/tsconfig.json", "mobile/base/tsconfig.json.j2"),
    ("apps/mobile/app/_layout.tsx", "mobile/base/app/_layout.tsx.j2"),
    ("apps/mobile/app/(tabs)/_layout.tsx", "mobile/base/app/(tabs)/_layout.tsx.j2"),
    ("apps/mobile/app/(tabs)/index.tsx", "mobile/base/app/(tabs)/index.tsx.j2"),
    ("apps/mobile/lib/api/client.ts", "mobile/base/lib/api/client.ts.j2"),
    ("apps/mobile/lib/storage/session.ts", "mobile/base/lib/storage/session.ts.j2"),
    ("apps/mobile/lib/telemetry/analytics.ts", "mobile/base/lib/telemetry/analytics.ts.j2"),
]

AUTH_MOBILE_FILES: list[tuple[str, str]] = [
    ("apps/mobile/app/(auth)/login.tsx", "mobile/base/app/(auth)/login.tsx.j2"),
    ("apps/mobile/app/(auth)/signup.tsx", "mobile/base/app/(auth)/signup.tsx.j2"),
]

BACKEND_BASE_FILES: list[tuple[str, str]] = [
    ("backend/app/main.py", "backend/base/app/main.py.j2"),
    ("backend/app/core/security.py", "backend/base/app/core/security.py.j2"),
    ("backend/app/db/database.py", "backend/base/app/db/database.py.j2"),
    ("backend/app/models/user.py", "backend/base/app/models/user.py.j2"),
    ("backend/app/schemas/auth.py", "backend/base/app/schemas/auth.py.j2"),
    ("backend/app/auth/service.py", "backend/base/app/auth/service.py.j2"),
    ("backend/app/auth/router.py", "backend/base/app/auth/router.py.j2"),
    ("backend/pyproject.toml", "backend/base/pyproject.toml.j2"),
    ("backend/.env.example", "backend/base/.env.example.j2"),
    ("README.md", "backend/base/README.md.j2"),
]

MODULE_FILES: dict[str, list[tuple[str, str]]] = {
    "payments_placeholder": [
        ("apps/mobile/app/paywall.tsx", "mobile/modules/payments_placeholder/app/paywall.tsx.j2"),
        ("backend/app/api/billing.py", "backend/modules/payments_placeholder/app/api/billing.py.j2"),
        (
            "backend/app/services/billing.py",
            "backend/modules/payments_placeholder/app/services/billing.py.j2",
        ),
    ],
    "list_detail_crud": [
        ("apps/mobile/app/(tabs)/list.tsx", "mobile/modules/list_detail/app/(tabs)/list.tsx.j2"),
        ("apps/mobile/app/(tabs)/detail.tsx", "mobile/modules/list_detail/app/(tabs)/detail.tsx.j2"),
        ("backend/app/api/items.py", "backend/modules/list_detail/app/api/items.py.j2"),
        ("backend/app/models/item.py", "backend/modules/list_detail/app/models/item.py.j2"),
    ],
    "form_flow": [
        (
            "apps/mobile/app/(tabs)/new-entry.tsx",
            "mobile/modules/form_flow/app/(tabs)/new-entry.tsx.j2",
        ),
    ],
    "settings": [
        (
            "apps/mobile/app/(tabs)/settings.tsx",
            "mobile/modules/settings/app/(tabs)/settings.tsx.j2",
        ),
    ],
    "notifications_placeholder": [
        (
            "apps/mobile/lib/notifications.ts",
            "mobile/modules/notifications/lib/notifications.ts.j2",
        ),
    ],
    "local_persistence": [
        ("apps/mobile/lib/db/local.ts", "mobile/base/lib/db/local.ts.j2"),
    ],
    "analytics_hook": [
        ("apps/mobile/lib/telemetry/analytics.ts", "mobile/base/lib/telemetry/analytics.ts.j2"),
    ],
}

BASE_ENV_VARS = [
    EnvVar(key="DATABASE_URL", example_value="sqlite+aiosqlite:///./app.db", description="DB path"),
    EnvVar(key="SECRET_KEY", example_value="change-me-in-production", description="JWT secret"),
    EnvVar(
        key="EXPO_PUBLIC_API_URL", example_value="http://localhost:8000", description="Backend URL"
    ),
]

PAYMENTS_ENV_VARS = [
    EnvVar(key="STRIPE_SECRET_KEY", example_value="sk_test_...", description="Stripe secret key"),
    EnvVar(
        key="STRIPE_WEBHOOK_SECRET", example_value="whsec_...", description="Stripe webhook secret"
    ),
]

ALWAYS_ON_MODULES = ["dashboard", "local_persistence", "analytics_hook"]


class BlueprintMapper:
    def _select_modules(self, spec: ProductSpec) -> list[str]:
        modules = list(ALWAYS_ON_MODULES)
        if spec.auth_required:
            modules.insert(0, "auth")
        if spec.payments_placeholder:
            modules.append("payments_placeholder")
        if spec.notifications:
            modules.append("notifications_placeholder")
        return modules

    def shell_file_plan(self, spec: ProductSpec) -> list[FilePlan]:
        """Mobile-only file plan for the shell pass (no backend)."""
        files = list(MOBILE_BASE_FILES)
        if spec.auth_required:
            files.extend(AUTH_MOBILE_FILES)
        modules = self._select_modules(spec)
        for module in modules:
            if module in MODULE_FILES:
                for path, template in MODULE_FILES[module]:
                    if path.startswith("apps/mobile"):
                        files.append((path, template))
        return [FilePlan(path=p, template=t, context_keys=[]) for p, t in files]

    def map(self, spec: ProductSpec) -> ArchitectureBlueprint:
        """Full file plan for both mobile and backend."""
        modules = self._select_modules(spec)
        files = list(MOBILE_BASE_FILES)
        if spec.auth_required:
            files.extend(AUTH_MOBILE_FILES)
        files.extend(BACKEND_BASE_FILES)
        for module in modules:
            if module in MODULE_FILES:
                files.extend(MODULE_FILES[module])

        file_plan = [FilePlan(path=p, template=t, context_keys=[]) for p, t in files]
        env_vars = list(BASE_ENV_VARS)
        if spec.payments_placeholder:
            env_vars.extend(PAYMENTS_ENV_VARS)

        return ArchitectureBlueprint(
            mobile_framework="expo",
            backend_framework="fastapi",
            selected_modules=modules,
            file_plan=file_plan,
            api_routes=[],
            db_entities=["User"] + [e.name for e in spec.data_entities],
            env_vars=env_vars,
        )
