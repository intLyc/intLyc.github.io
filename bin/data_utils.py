"""Shared validation and safe-write helpers for dynamic site data."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class DataValidationError(RuntimeError):
    """Raised when a remote response is unsafe to publish."""


def today_iso() -> str:
    """Return today's date in the machine's configured local timezone."""

    return datetime.now().astimezone().date().isoformat()


def load_yaml_mapping(path: str | Path) -> dict[str, Any] | None:
    """Load a YAML mapping, returning None when the file does not exist."""

    source = Path(path)
    if not source.exists():
        return None
    with source.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DataValidationError(f"{source} must contain a YAML mapping")
    return value


def atomic_dump_yaml(path: str | Path, value: dict[str, Any]) -> None:
    """Write YAML via a sibling temporary file, then atomically replace it."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, allow_unicode=True, sort_keys=True, width=1000)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
