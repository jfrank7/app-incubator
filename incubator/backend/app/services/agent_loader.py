from pathlib import Path

_AGENTS_DIR = Path(__file__).parent.parent / "library" / "agents"


def load_agent_instructions(agent_filename: str) -> str:
    """Load agent system prompt from library/agents/<filename>.

    Raises FileNotFoundError if agent file doesn't exist.
    """
    path = _AGENTS_DIR / agent_filename
    if not path.exists():
        raise FileNotFoundError(f"Agent instructions not found: {path}")
    return path.read_text()


def list_agents() -> list[str]:
    return [f.name for f in sorted(_AGENTS_DIR.glob("*.md"))]
