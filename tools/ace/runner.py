"""Command execution utilities for ACE."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

from .artefacts import CommandResult


class CommandExecutionError(RuntimeError):
    """Raised when a mandatory command fails."""

    def __init__(self, message: str, result: CommandResult):
        super().__init__(message)
        self.result = result


def _resolve_cwd(cwd: str) -> Path:
    path = Path(cwd).resolve()
    return path


def run_command(
    name: str,
    command: Iterable[str],
    *,
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    optional: bool = False,
) -> CommandResult:
    """Execute a shell command, capturing stdout/stderr and timing information."""

    command_list = [str(part) for part in command]
    if not command_list:
        raise ValueError("Command list must not be empty")

    executable = shutil.which(command_list[0])
    if executable is None:
        status = "skipped"
        started_at = datetime.now(timezone.utc)
        finished_at = started_at
        message = f"Executable '{command_list[0]}' not found in PATH"
        return CommandResult(
            name=name,
            command=command_list,
            cwd=str(_resolve_cwd(cwd)),
            status=status,
            exit_code=-1,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_seconds=0.0,
            stdout="",
            stderr=message,
        )

    started_at = datetime.now(timezone.utc)
    start_monotonic = time.monotonic()
    process = subprocess.run(
        command_list,
        cwd=_resolve_cwd(cwd),
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )
    duration = time.monotonic() - start_monotonic
    finished_at = datetime.now(timezone.utc)

    status: str
    if process.returncode == 0:
        status = "success"
    else:
        status = "failure"

    result = CommandResult(
        name=name,
        command=command_list,
        cwd=str(_resolve_cwd(cwd)),
        status=status,
        exit_code=process.returncode,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_seconds=duration,
        stdout=process.stdout,
        stderr=process.stderr,
    )

    if status == "failure" and not optional:
        raise CommandExecutionError(
            f"Command '{name}' failed with exit code {process.returncode}", result
        )
    return result


__all__ = ["CommandExecutionError", "run_command"]
