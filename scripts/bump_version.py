#!/usr/bin/env python3
"""Bump version, commit, tag y push para disparar el release en GitHub Actions.

Uso:
    python scripts/bump_version.py 0.2.0
    python scripts/bump_version.py v0.2.0  (el prefijo v es opcional)
"""

import re
import subprocess
import sys


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def bump(new_version: str) -> None:
    ver = new_version.lstrip("v")
    parts = ver.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        sys.exit("Error: la versión debe tener formato MAJOR.MINOR.PATCH (ej: 0.2.0)")

    major, minor, patch = parts
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
        r"(u'FileVersion',\s+u')\d+\.\d+\.\d+(')",
        rf"\g<1>{ver}\2",
        content,
    )
    content = re.sub(
        r"(u'ProductVersion',\s+u')\d+\.\d+\.\d+(')",
        rf"\g<1>{ver}\2",
        content,
    )

    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(content)

    with open("version.py", "w", encoding="utf-8") as f:
        f.write(f'APP_VERSION = "{ver}"\n')

    tag = f"v{ver}"

    run(["git", "add", "version_info.txt", "version.py"])
    run(["git", "commit", "-m", f"chore(release): bump version to {ver}"])
    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
    run(["git", "push", "--follow-tags"])

    print(f"\nTag {tag} publicado. GitHub Actions compilará y creará el release.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/bump_version.py <version>  (ej: 0.2.0)")
    bump(sys.argv[1])
