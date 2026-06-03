"""Safe subprocess execution – never uses shell=True."""
import subprocess
from typing import List, Optional, Tuple

class ShellError(Exception):
    """Raised when a subprocess command fails."""
    def __init__(self, cmd: List[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{' '.join(cmd)}' failed with code {returncode}: {stderr}")

def run(cmd: List[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
    """
    Execute a command securely (no shell).
    Returns (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        raise ShellError(cmd, -1, f"Command not found: {cmd[0]}")

def run_sudo(cmd: List[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
    """Run a command with sudo (password-less expected)."""
    return run(["sudo"] + cmd, timeout=timeout)

def run_checked(cmd: List[str], timeout: Optional[float] = None) -> str:
    """
    Run a command and raise ShellError if it fails.
    Returns stdout on success.
    """
    rc, out, err = run(cmd, timeout)
    if rc != 0:
        raise ShellError(cmd, rc, err)
    return out

def run_sudo_checked(cmd: List[str], timeout: Optional[float] = None) -> str:
    """Checked version of run_sudo."""
    return run_checked(["sudo"] + cmd, timeout)