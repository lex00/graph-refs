#!/usr/bin/env python3
"""Create a GitHub release with tag and changelog notes.

Usage:
    python scripts/release.py           # Release current version
    python scripts/release.py --dry-run # Show what would happen
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    content = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def get_changelog_section(version: str) -> str:
    """Extract the changelog section for a specific version."""
    content = CHANGELOG.read_text()

    # Pattern to match version section
    # Matches ## [X.Y.Z] - YYYY-MM-DD or ## [X.Y.Z]
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return f"Release v{version}"

    return match.group(1).strip()


def run(cmd: list[str], dry_run: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally as dry-run."""
    print(f"  $ {' '.join(cmd)}")
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, check=check, capture_output=True, text=True, cwd=PROJECT_ROOT)


def main() -> int:
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("DRY RUN - no changes will be made\n")

    # Get version and changelog
    version = get_current_version()
    tag = f"v{version}"
    notes = get_changelog_section(version)

    print(f"Version: {version}")
    print(f"Tag: {tag}")
    print(f"\nRelease notes:\n{'-' * 40}")
    print(notes)
    print(f"{'-' * 40}\n")

    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    if result.stdout.strip():
        print("Error: Uncommitted changes detected. Commit or stash them first.")
        return 1

    # Check if tag already exists
    result = subprocess.run(
        ["git", "tag", "-l", tag],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    if result.stdout.strip():
        print(f"Error: Tag {tag} already exists.")
        return 1

    # Check gh is authenticated
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Error: gh CLI not authenticated. Run 'gh auth login' first.")
        return 1

    print("Creating release...\n")

    # Create and push tag
    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], dry_run=dry_run)
    run(["git", "push", "origin", tag], dry_run=dry_run)

    # Create GitHub release
    run([
        "gh", "release", "create", tag,
        "--title", tag,
        "--notes", notes,
    ], dry_run=dry_run)

    print(f"\nRelease {tag} created successfully!")
    print(f"View at: https://github.com/lex00/graph-refs/releases/tag/{tag}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
