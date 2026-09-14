"""Load local project configuration without overriding the process environment."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env(path: str | Path | None = None) -> bool:
    """Load `.env` from the working directory, preserving existing variables."""
    env_path = Path(path) if path is not None else Path.cwd() / ".env"
    return load_dotenv(dotenv_path=env_path, override=False)
