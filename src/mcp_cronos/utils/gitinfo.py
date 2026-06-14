"""Best-effort git repository/branch detection for diary entries.

Reads the repository name and current branch from a git working directory so
entry tools can fill the `repository` and `branch` fields automatically. The
target directory is an explicit path or the server process working directory;
any failure (not a git repo, git missing) yields (None, None) without raising,
so detection never blocks entry creation.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def _run_git(args: list[str], cwd: str) -> Optional[str]:
    """Run a git command in cwd and return stripped stdout, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def detect_git_info(working_dir: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Detect (repository_name, branch) from a git working directory.

    Args:
        working_dir: Directory to inspect; defaults to the current working
            directory of the server process.

    Returns:
        (repository_name, branch). repository_name is the basename of the repo
        top-level. Either element is None when it cannot be determined.
    """
    cwd = working_dir or os.getcwd()
    toplevel = _run_git(["rev-parse", "--show-toplevel"], cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    repository = Path(toplevel).name if toplevel else None
    return repository, branch
