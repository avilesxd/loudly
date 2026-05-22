#!/usr/bin/env python3
"""Auto-bump: determina versión semántica desde commits y publica el release.

Reglas (Conventional Commits):
  BREAKING CHANGE / feat!: / fix!:  → MAJOR
  feat:                              → MINOR
  fix: / perf:                       → PATCH
  Cualquier otra cosa                → sin release
"""

import os
import re
import subprocess


def run(cmd: list[str], capture: bool = False) -> str:
    result = subprocess.run(cmd, check=True, capture_output=capture, text=capture)
    return result.stdout.strip() if capture else ""


def get_latest_tag() -> str:
    try:
        return run(["git", "describe", "--tags", "--abbrev=0"], capture=True)
    except subprocess.CalledProcessError:
        return "v0.0.0"


def get_commits_since(tag: str) -> list[str]:
    output = run(["git", "log", f"{tag}..HEAD", "--pretty=format:%s"], capture=True)
    return [line for line in output.splitlines() if line.strip()]


def determine_bump(commits: list[str]) -> str:
    if not commits:
        return "none"

    for msg in commits:
        if re.match(r"^(feat|fix|perf|refactor|docs)(\(.+\))?\!:", msg):
            return "major"
        if "BREAKING CHANGE" in msg:
            return "major"

    for msg in commits:
        if re.match(r"^feat(\(.+\))?:", msg):
            return "minor"

    for msg in commits:
        if re.match(r"^(fix|perf)(\(.+\))?:", msg):
            return "patch"

    return "none"


def calc_new_version(current: str, bump: str) -> str:
    ver = current.lstrip("v")
    major, minor, patch = (int(x) for x in ver.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def update_version_info(ver: str) -> None:
    major, minor, patch = ver.split(".")
    tuple_ver = f"({major}, {minor}, {patch}, 0)"

    with open("version_info.txt", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"filevers=\(\d+, \d+, \d+, \d+\)", f"filevers={tuple_ver}", content
    )
    content = re.sub(
        r"prodvers=\(\d+, \d+, \d+, \d+\)", f"prodvers={tuple_ver}", content
    )
    content = re.sub(
        r"(u'FileVersion',\s+u')\d+\.\d+\.\d+(')", rf"\g<1>{ver}\2", content
    )
    content = re.sub(
        r"(u'ProductVersion',\s+u')\d+\.\d+\.\d+(')", rf"\g<1>{ver}\2", content
    )

    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(content)

    with open("version.py", "w", encoding="utf-8") as f:
        f.write(f'APP_VERSION = "{ver}"\n')


def set_github_output(key: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main() -> None:
    latest_tag = get_latest_tag()
    commits = get_commits_since(latest_tag)

    print(f"Último tag: {latest_tag}")
    print(f"Commits desde el tag: {len(commits)}")
    for c in commits:
        print(f"  {c}")

    bump = determine_bump(commits)
    print(f"Tipo de bump: {bump}")

    if bump == "none":
        print("Sin commits releaseables. Nada que hacer.")
        set_github_output("released", "false")
        return

    new_version = calc_new_version(latest_tag, bump)
    new_tag = f"v{new_version}"
    print(f"Nueva versión: {new_tag}")

    update_version_info(new_version)

    run(["git", "config", "user.name", "github-actions[bot]"])
    run(
        [
            "git",
            "config",
            "user.email",
            "github-actions[bot]@users.noreply.github.com",
        ]
    )
    run(["git", "add", "version_info.txt", "version.py"])
    run(["git", "commit", "-m", f"chore(release): bump version to {new_version}"])
    run(["git", "tag", "-a", new_tag, "-m", f"Release {new_tag}"])
    run(["git", "push", "--follow-tags"])

    set_github_output("released", "true")
    set_github_output("new_tag", new_tag)

    print(f"\nTag {new_tag} publicado.")


if __name__ == "__main__":
    main()
