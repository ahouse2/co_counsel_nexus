from __future__ import annotations

import shutil
import subprocess
import tempfile
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Sequence


class SandboxExecutionError(RuntimeError):
    """Raised when the sandbox fails to apply a diff or run validation commands."""


@dataclass(slots=True)
class SandboxCommandResult:
    """Result of executing a single validation command inside the sandbox."""

    command: List[str]
    return_code: int
    stdout: str
    stderr: str
    duration_ms: float

    def to_json(self) -> dict:
        return {
            "command": list(self.command),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_json(cls, payload: dict) -> "SandboxCommandResult":
        return cls(
            command=[str(item) for item in payload.get("command", [])],
            return_code=int(payload.get("return_code", 0)),
            stdout=str(payload.get("stdout", "")),
            stderr=str(payload.get("stderr", "")),
            duration_ms=float(payload.get("duration_ms", 0.0)),
        )


@dataclass(slots=True)
class SandboxExecutionResult:
    """Structured result returned after validating a diff inside the sandbox."""

    success: bool
    commands: List[SandboxCommandResult]
    workspace_id: str

    def to_json(self) -> dict:
        return {
            "success": self.success,
            "workspace_id": self.workspace_id,
            "commands": [command.to_json() for command in self.commands],
        }

    @classmethod
    def from_json(cls, payload: dict) -> "SandboxExecutionResult":
        return cls(
            success=bool(payload.get("success", False)),
            workspace_id=str(payload.get("workspace_id", "")),
            commands=[SandboxCommandResult.from_json(item) for item in payload.get("commands", [])],
        )


_CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess]


def _default_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


GIT_APPLY_COMMAND: List[str] = ["git", "apply", "--whitespace=nowarn"]


class SandboxExecutionHarness:
    """Creates a disposable workspace, applies a diff, and runs lint/tests."""

    def __init__(
        self,
        repo_root: Path,
        commands: Iterable[Sequence[str]] | None = None,
        *,
        command_runner: _CommandRunner | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        if not self.repo_root.exists():
            raise FileNotFoundError(f"Repository root {self.repo_root} does not exist")
        self.commands = [list(cmd) for cmd in (commands or [])]
        self.command_runner = command_runner or _default_runner

    def validate(self, diff: str) -> SandboxExecutionResult:
        with tempfile.TemporaryDirectory(prefix="dev-agent-") as tmpdir:
            workspace_root = Path(tmpdir)
            workspace = workspace_root / "workspace"
            self._materialise_workspace(workspace)
            workspace_id = workspace_root.name
            results: List[SandboxCommandResult] = []
            success = True
            if diff.strip():
                apply_result = self._apply_diff(workspace, diff)
                results.append(apply_result)
                if apply_result.return_code != 0:
                    return SandboxExecutionResult(
                        success=False,
                        commands=results,
                        workspace_id=workspace_id,
                    )
            for command in self.commands:
                result = self._run_command(workspace, command)
                results.append(result)
                if result.return_code != 0:
                    success = False
                    break
            return SandboxExecutionResult(success=success, commands=results, workspace_id=workspace_id)

    def _materialise_workspace(self, workspace: Path) -> None:
        shutil.copytree(self.repo_root, workspace, dirs_exist_ok=True)

    def _apply_diff(self, workspace: Path, diff: str) -> SandboxCommandResult:
        started = time.perf_counter()
        process = subprocess.run(
            GIT_APPLY_COMMAND,
            input=diff.encode("utf-8"),
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        return SandboxCommandResult(
            command=list(GIT_APPLY_COMMAND),
            return_code=process.returncode,
            stdout=process.stdout or "",
            stderr=process.stderr or "",
            duration_ms=round(duration_ms, 2),
        )

    def _run_command(self, workspace: Path, command: Sequence[str]) -> SandboxCommandResult:
        started = time.perf_counter()
        process = self.command_runner(command, workspace)
        duration_ms = (time.perf_counter() - started) * 1000.0
        if not isinstance(process, subprocess.CompletedProcess):
            raise SandboxExecutionError("Command runner must return subprocess.CompletedProcess instances")
        return SandboxCommandResult(
            command=list(command),
            return_code=process.returncode,
            stdout=process.stdout or "",
            stderr=process.stderr or "",
            duration_ms=round(duration_ms, 2),
        )
