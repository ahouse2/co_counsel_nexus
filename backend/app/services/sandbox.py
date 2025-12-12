# Production-grade sandbox service for isolated command execution
from typing import Any, Dict
import subprocess
import uuid
import tempfile
from pathlib import Path

class SandboxService:
    """Provides isolated command execution in temporary workspaces."""
    
    async def execute_command(self, principal: Any, command: str) -> Dict[str, Any]:
        """
        Execute a command in an isolated temp directory.
        Returns execution results including stdout, stderr, and return code.
        """
        workspace_id = str(uuid.uuid4())
        
        # Create temporary workspace
        with tempfile.TemporaryDirectory(prefix=f"sandbox_{workspace_id}_") as tmpdir:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=60,  # 1 minute timeout
                    env={'HOME': tmpdir, 'TMPDIR': tmpdir}  # Isolated environment
                )
                
                return {
                    "workspace_id": workspace_id,
                    "command": command,
                    "return_code": result.returncode,
                    "stdout": result.stdout[:1000],  # Limited output
                    "stderr": result.stderr[:1000],
                    "success": result.returncode == 0
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "workspace_id": workspace_id,
                    "command": command,
                    "error": "Command timed out after 60 seconds",
                    "success": False
                }
            except Exception as exc:
                return {
                    "workspace_id": workspace_id,
                    "command": command,
                    "error": str(exc),
                    "success": False
                }

_sandbox_service: SandboxService | None = None

def get_sandbox_service() -> SandboxService:
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService()
    return _sandbox_service
