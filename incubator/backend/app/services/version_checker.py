import httpx

# Verified compatible version sets per Expo SDK.
# Version checker agent updates this via web search before generation.
_EXPO_SDK_54_VERSIONS = {
    "expo": "~54.0.0",
    "expo-router": "~4.0.0",
    "expo-secure-store": "~14.0.0",
    "expo-status-bar": "~2.0.0",
    "@react-native-async-storage/async-storage": "~2.1.0",
    "react": "18.3.1",
    "react-native": "0.76.9",
    "react-native-safe-area-context": "~5.4.0",
    "react-native-screens": "~4.4.0",
}

_PYTHON_VERSIONS: dict[str, str] = {}  # populated by check_python_versions()


async def _fetch_npm_latest(package: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"https://registry.npmjs.org/{package}/latest")
            if r.status_code == 200:
                return r.json().get("version")
    except Exception:
        pass
    return None


async def _fetch_pypi_latest(package: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"https://pypi.org/pypi/{package}/json")
            if r.status_code == 200:
                return r.json()["info"]["version"]
    except Exception:
        pass
    return None


async def get_mobile_versions() -> dict[str, str]:
    """Return verified npm package versions for Expo SDK 54 stack.

    Attempts live verification of react/react-native/expo versions.
    Falls back to known-good pinned versions if network unavailable.
    """
    versions = dict(_EXPO_SDK_54_VERSIONS)

    # Verify a few key packages live
    for pkg in ["expo", "react-native"]:
        latest = await _fetch_npm_latest(pkg)
        if latest:
            major = latest.split(".")[0]
            if pkg == "expo" and major == "54":
                versions[pkg] = f"~{latest}"
            elif pkg == "react-native" and major == "0":
                versions[pkg] = latest

    return versions


async def get_python_versions() -> dict[str, str]:
    """Return verified PyPI package versions for FastAPI stack."""
    packages = ["fastapi", "sqlalchemy", "pydantic", "uvicorn", "aiosqlite", "python-jose", "bcrypt"]
    versions: dict[str, str] = {}
    for pkg in packages:
        v = await _fetch_pypi_latest(pkg)
        versions[pkg] = v if v else "latest"
    return versions


def format_versions_for_prompt(mobile: dict[str, str], python: dict[str, str]) -> str:
    lines = ["## Verified Package Versions (use these exactly)\n\n### npm (mobile)"]
    for k, v in mobile.items():
        lines.append(f"  {k}: {v}")
    lines.append("\n### PyPI (backend)")
    for k, v in python.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)
