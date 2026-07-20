#!/usr/bin/env python3
"""Refresh the text-only counters in the profile README."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


PROFILE_USER = os.environ.get("PROFILE_USER", "Ivansost")
NEETCODE_REPO = os.environ.get("NEETCODE_REPO", "neetcode-submissions")
NEETCODE_ROOT = "Data Structures & Algorithms/"
START_MARKER = "<!-- PROFILE-STATS:START -->"
END_MARKER = "<!-- PROFILE-STATS:END -->"
README_PATH = Path(__file__).resolve().parents[1] / "README.md"


def github_api(endpoint: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Ivansost-profile-counter",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"https://api.github.com{endpoint}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def get_public_repository_count() -> int:
    user = github_api(f"/users/{quote(PROFILE_USER)}")
    if not isinstance(user, dict) or not isinstance(user.get("public_repos"), int):
        raise RuntimeError("GitHub did not return a public repository count")
    return user["public_repos"]


def get_neetcode_problem_count() -> int:
    owner = quote(PROFILE_USER)
    repository = quote(NEETCODE_REPO)
    repo = github_api(f"/repos/{owner}/{repository}")
    if not isinstance(repo, dict) or not isinstance(repo.get("default_branch"), str):
        raise RuntimeError("GitHub did not return the NeetCode repository branch")

    branch = quote(repo["default_branch"], safe="")
    tree = github_api(f"/repos/{owner}/{repository}/git/trees/{branch}?recursive=1")
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        raise RuntimeError("GitHub did not return the NeetCode repository tree")
    if tree.get("truncated"):
        raise RuntimeError("The NeetCode repository tree was truncated")

    solved_problems: set[str] = set()
    for item in tree["tree"]:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        item_path = item.get("path")
        if not isinstance(item_path, str) or not item_path.startswith(NEETCODE_ROOT):
            continue

        relative_path = item_path[len(NEETCODE_ROOT) :]
        problem, separator, filename = relative_path.partition("/")
        if separator and problem and re.fullmatch(r"submission-\d+\.[A-Za-z0-9]+", filename):
            solved_problems.add(problem)

    return len(solved_problems)


def render_stats(public_repositories: int, solved_problems: int) -> str:
    return (
        f"{START_MARKER}\n"
        "```text\n"
        f"public_repositories .... {public_repositories}\n"
        f"neetcode_dsa_solved .... {solved_problems} unique problems\n"
        "```\n"
        f"{END_MARKER}"
    )


def update_readme(public_repositories: int, solved_problems: int) -> bool:
    current = README_PATH.read_text(encoding="utf-8")
    marker_pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    if marker_pattern.search(current) is None:
        raise RuntimeError("Profile stats markers are missing from README.md")

    updated = marker_pattern.sub(
        render_stats(public_repositories, solved_problems),
        current,
        count=1,
    )
    if updated == current:
        return False

    README_PATH.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    repositories = get_public_repository_count()
    solved = get_neetcode_problem_count()
    changed = update_readme(repositories, solved)
    outcome = "updated" if changed else "already current"
    print(f"Profile stats {outcome}: {repositories} repositories, {solved} solved problems")


if __name__ == "__main__":
    main()
