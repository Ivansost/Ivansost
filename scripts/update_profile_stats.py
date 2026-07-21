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
STATS_DIR = README_PATH.parent / "assets" / "stats"
DARK_STATS_PATH = STATS_DIR / "profile-stats-dark-v2.svg"
LIGHT_STATS_PATH = STATS_DIR / "profile-stats-light-v2.svg"


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


def render_stats_svg(
    public_repositories: int,
    solved_problems: int,
    *,
    background: str,
    foreground: str,
    divider: str,
) -> str:
    return f'''<svg width="620" height="78" viewBox="0 0 620 78" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Profile stats</title>
  <desc id="desc">{public_repositories} public repositories and {solved_problems} NeetCode data structures and algorithms problems solved.</desc>
  <rect x="1" y="1" width="618" height="76" rx="8" fill="{background}" stroke="{foreground}" stroke-width="2"/>
  <path d="M310 14V64" stroke="{divider}" stroke-width="1"/>
  <text x="155" y="37" fill="{foreground}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="28" font-weight="700" text-anchor="middle">{public_repositories}</text>
  <text x="155" y="59" fill="{foreground}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" text-anchor="middle">public repositories</text>
  <text x="465" y="37" fill="{foreground}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="28" font-weight="700" text-anchor="middle">{solved_problems}</text>
  <text x="465" y="59" fill="{foreground}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" text-anchor="middle">NeetCode data structures &amp; algorithms problems solved</text>
</svg>
'''


def update_stats_assets(public_repositories: int, solved_problems: int) -> bool:
    assets = {
        DARK_STATS_PATH: render_stats_svg(
            public_repositories,
            solved_problems,
            background="#0d1117",
            foreground="#f0f6fc",
            divider="#8c959f",
        ),
        LIGHT_STATS_PATH: render_stats_svg(
            public_repositories,
            solved_problems,
            background="#ffffff",
            foreground="#24292f",
            divider="#57606a",
        ),
    }
    changed = False
    for path, contents in assets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == contents:
            continue
        path.write_text(contents, encoding="utf-8")
        changed = True
    return changed


def render_stats(public_repositories: int, solved_problems: int) -> str:
    return (
        f"{START_MARKER}\n"
        '<p align="center">\n'
        "  <picture>\n"
        '    <source media="(prefers-color-scheme: dark)" srcset="./assets/stats/profile-stats-dark-v2.svg">\n'
        '    <source media="(prefers-color-scheme: light)" srcset="./assets/stats/profile-stats-light-v2.svg">\n'
        f'    <img src="./assets/stats/profile-stats-light-v2.svg" alt="{public_repositories} public repositories and {solved_problems} NeetCode data structures and algorithms problems solved" width="620">\n'
        "  </picture>\n"
        "</p>\n"
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
    readme_changed = update_readme(repositories, solved)
    assets_changed = update_stats_assets(repositories, solved)
    changed = readme_changed or assets_changed
    outcome = "updated" if changed else "already current"
    print(f"Profile stats {outcome}: {repositories} repositories, {solved} solved problems")


if __name__ == "__main__":
    main()
