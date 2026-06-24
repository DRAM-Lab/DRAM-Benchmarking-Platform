"""Shared project-root resolution for all OpenDRAMBench packages."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_FALLBACK_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def resolve_project_root() -> Path:
    """Return the platform repository root.

    Honors ``OPEN_DRAM_PROJECT_ROOT`` so shell wrappers and editable installs
    agree when the checkout path differs from ``pip install -e`` source (e.g.
    ``/home/...`` vs ``/data1/...`` on shared lab machines).
    """
    env = os.environ.get("OPEN_DRAM_PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _FALLBACK_ROOT
