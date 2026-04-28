from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.schemas.form import ArchitectureBlueprint, ProductSpec

TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"


class ScaffolderService:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_ROOT)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def _build_context(self, spec: ProductSpec, blueprint: ArchitectureBlueprint) -> dict:
        return {
            "app_name": spec.app_name,
            "app_slug": spec.app_slug,
            "goal": spec.goal,
            "target_user": spec.target_user,
            "offline_support": spec.offline_support,
            "notifications": spec.notifications,
            "auth_required": spec.auth_required,
            "payments_placeholder": spec.payments_placeholder,
            "style_notes": spec.style_notes,
            "non_goals": spec.non_goals,
            "screens": spec.screens,
            "data_entities": spec.data_entities,
            "features": spec.features,
            "selected_modules": blueprint.selected_modules,
            "api_routes": blueprint.api_routes,
            "db_entities": blueprint.db_entities,
            "env_vars": blueprint.env_vars,
            "shell_mode": False,
        }

    def scaffold(
        self,
        spec: ProductSpec,
        blueprint: ArchitectureBlueprint,
        output_dir: Path,
        extra_context: dict | None = None,
    ) -> list[str]:
        context = self._build_context(spec, blueprint)
        if extra_context:
            context.update(extra_context)
        written: list[str] = []

        for file_plan in blueprint.file_plan:
            template = self.env.get_template(file_plan.template)
            rendered = template.render(**context)
            dest = output_dir / file_plan.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")
            written.append(str(dest))

        return written
