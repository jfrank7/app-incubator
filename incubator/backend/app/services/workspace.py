"""Per-run workspace: shared communication space between pipeline agents.

Each run gets ~/generated-apps/<run-id>/workspace/ with:
  index.md        — shared state; agents read on entry, update on exit
  agent-log.md    — append-only action log
  spec.json       — written by spec agent, read by all subsequent agents
  blueprint.json  — written by blueprint agent, read by file generator
  versions.json   — written by version checker, read by file generator
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


class WorkspaceService:
    def _workspace_dir(self, run_id: str) -> Path:
        d = settings.generated_apps_path / run_id / "workspace"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Index (shared state) ──────────────────────────────────────────────────

    def read_index(self, run_id: str) -> str:
        path = self._workspace_dir(run_id) / "index.md"
        if not path.exists():
            return "(No workspace context yet — this is the first agent in the run.)"
        return path.read_text()

    def init_index(self, run_id: str, app_name: str = "unknown") -> None:
        path = self._workspace_dir(run_id) / "index.md"
        if path.exists():
            return
        content = f"""# Run Workspace: {run_id}

## App: {app_name}
## Started: {_now()}

## Agent log summary
(Updated by each agent as it completes)

## Key decisions
(Recorded by agents as they make architectural choices)

## File registry
(Updated by file generator agent)
"""
        path.write_text(content)

    def update_index(
        self,
        run_id: str,
        agent: str,
        summary: str,
        decisions: list[str] | None = None,
        files_written: list[str] | None = None,
    ) -> None:
        path = self._workspace_dir(run_id) / "index.md"
        current = path.read_text() if path.exists() else ""

        entry = f"\n### [{_now()}] {agent}\n{summary}\n"
        if decisions:
            entry += "\nDecisions:\n" + "\n".join(f"- {d}" for d in decisions) + "\n"
        if files_written:
            entry += "\nFiles written:\n" + "\n".join(f"- {f}" for f in files_written) + "\n"

        # Append under the agent log summary section
        if "## Agent log summary" in current:
            updated = current.replace(
                "## Agent log summary\n(Updated by each agent as it completes)",
                "## Agent log summary" + entry,
            )
            # If already has entries, just append
            if updated == current:
                updated = current + entry
        else:
            updated = current + entry

        path.write_text(updated)
        self._append_log(run_id, agent, summary)

    # ── Structured artifacts ──────────────────────────────────────────────────

    def write_artifact(self, run_id: str, filename: str, data: dict | list) -> None:
        path = self._workspace_dir(run_id) / filename
        path.write_text(json.dumps(data, indent=2))

    def read_artifact(self, run_id: str, filename: str) -> dict | list | None:
        path = self._workspace_dir(run_id) / filename
        if not path.exists():
            return None
        return json.loads(path.read_text())

    # ── Append-only log ───────────────────────────────────────────────────────

    def _append_log(self, run_id: str, agent: str, message: str) -> None:
        path = self._workspace_dir(run_id) / "agent-log.md"
        line = f"[{_now()}] [{agent}] {message}\n"
        with path.open("a") as f:
            f.write(line)

    def log(self, run_id: str, agent: str, message: str) -> None:
        self._append_log(run_id, agent, message)

    def read_log(self, run_id: str) -> str:
        path = self._workspace_dir(run_id) / "agent-log.md"
        if not path.exists():
            return ""
        return path.read_text()

    # ── File registry (for file generator progress) ───────────────────────────

    def register_file(self, run_id: str, file_path: str, status: str = "generated") -> None:
        registry_path = self._workspace_dir(run_id) / "file-registry.json"
        registry: dict = {}
        if registry_path.exists():
            registry = json.loads(registry_path.read_text())
        registry[file_path] = {"status": status, "at": _now()}
        registry_path.write_text(json.dumps(registry, indent=2))

    def get_registry(self, run_id: str) -> dict:
        registry_path = self._workspace_dir(run_id) / "file-registry.json"
        if not registry_path.exists():
            return {}
        return json.loads(registry_path.read_text())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Singleton
workspace = WorkspaceService()
