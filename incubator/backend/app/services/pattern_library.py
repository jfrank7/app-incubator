from pathlib import Path

_PATTERNS_DIR = Path(__file__).parent.parent / "library" / "patterns"

_FILE_PATTERN_MAP: dict[str, list[str]] = {
    # Mobile patterns by path prefix / filename
    "_layout.tsx": ["expo-router-shell.md"],
    "(tabs)/_layout.tsx": ["expo-router-shell.md"],
    "(auth)/login.tsx": ["expo-auth-flow.md"],
    "(auth)/signup.tsx": ["expo-auth-flow.md"],
    "lib/storage/session.tsx": ["expo-auth-flow.md"],
    "lib/api/client.ts": ["expo-api-client.md"],
    # Backend patterns by path prefix
    "backend/app/main.py": ["fastapi-base.md"],
    "backend/app/db/": ["fastapi-base.md"],
    "backend/app/models/": ["fastapi-crud.md", "fastapi-base.md"],
    "backend/app/api/": ["fastapi-crud.md"],
    "backend/app/auth/": ["fastapi-base.md"],
}


def get_patterns_for_file(file_path: str) -> str:
    matched: set[str] = set()
    for key, pattern_files in _FILE_PATTERN_MAP.items():
        if key in file_path:
            matched.update(pattern_files)
    if not matched:
        # Default: give router shell for mobile, base for backend
        if file_path.startswith("apps/mobile"):
            matched.add("expo-router-shell.md")
        elif file_path.startswith("backend/"):
            matched.add("fastapi-base.md")
    return _load_patterns(matched)


def get_all_patterns() -> str:
    all_files = {f.name for f in _PATTERNS_DIR.glob("*.md")}
    return _load_patterns(all_files)


def _load_patterns(filenames: set[str]) -> str:
    parts: list[str] = []
    for name in sorted(filenames):
        path = _PATTERNS_DIR / name
        if path.exists():
            parts.append(path.read_text())
    return "\n\n---\n\n".join(parts)
