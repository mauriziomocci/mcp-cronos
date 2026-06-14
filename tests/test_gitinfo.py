"""Tests for mcp_cronos.utils.gitinfo (git repository/branch detection)."""

import subprocess


def _init_repo(path, branch="feature-x"):
    subprocess.run(["git", "init", "-b", branch, str(path)], check=True, capture_output=True)
    (path / "file.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "init"],
        check=True, capture_output=True,
    )


def test_detect_git_info_returns_repo_and_branch(tmp_path):
    from mcp_cronos.utils.gitinfo import detect_git_info

    repo = tmp_path / "myrepo"
    repo.mkdir()
    _init_repo(repo, branch="feature-x")

    repository, branch = detect_git_info(str(repo))
    assert repository == "myrepo"
    assert branch == "feature-x"


def test_detect_git_info_non_git_dir_returns_none(tmp_path):
    from mcp_cronos.utils.gitinfo import detect_git_info

    plain = tmp_path / "plain"
    plain.mkdir()
    repository, branch = detect_git_info(str(plain))
    assert repository is None
    assert branch is None
