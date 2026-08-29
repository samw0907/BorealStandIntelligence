# boreal-stand-intelligence/fi_forest_data/config.py
"""Secrets and environment loading.

The only credential the pipeline uses is a free NLS open-data API key for the
2020+ laser scanning product (Module A). It lives in config/.env (gitignored,
never committed) as NLS_API_KEY. This module loads it into the environment and
hands it to the fetch code; it is never logged or written to any output.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

_LOADED = False


def load_env(dotenv_path: str | Path = "config/.env") -> None:
    """Load config/.env into os.environ once (no-op if the file is absent)."""
    global _LOADED
    if _LOADED:
        return
    p = Path(dotenv_path)
    if load_dotenv is not None and p.exists():
        load_dotenv(p, override=False)
    _LOADED = True


def get_secret(name: str, *, dotenv_path: str | Path = "config/.env") -> str:
    """Return a required secret from the environment (loading config/.env first)."""
    load_env(dotenv_path)
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"{name} not set. Add it to config/.env (gitignored) - see docs/DATA_SOURCES.md section 4."
        )
    return val
