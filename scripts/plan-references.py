"""Work out what the release for this corpus version is still missing.

A version is a tag on the commit. Its release holds the metafiles and the
references for every size in sizes.txt, so whatever you download from one
release agrees with itself. Sizes come from sizes.txt, corpora from the commit,
and what already exists from the release. The difference is the work.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZES = ROOT / "sizes.txt"
VERSION = re.compile(r"v\d+(?:\.\d+)*")


def git(*args):
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise SystemExit(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def version():
    tags = [tag for tag in git("tag", "--points-at", "HEAD").split() if VERSION.fullmatch(tag)]
    if not tags:
        raise SystemExit(
            "No version tag on this commit. Tag it first, for example:\n"
            "  git tag v1 && git push origin v1"
        )
    return max(tags, key=lambda tag: [int(part) for part in tag[1:].split(".")])


def wanted_sizes():
    sizes = []
    for number, raw in enumerate(SIZES.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip().lower()
        if not line:
            continue
        width, _, height = line.partition("x")
        try:
            width, height = int(width), int(height)
        except ValueError:
            raise SystemExit(f"sizes.txt line {number}: expected WIDTHxHEIGHT, got {raw.strip()!r}")
        if width < 1 or height < 1:
            raise SystemExit(f"sizes.txt line {number}: dimensions must be positive")
        sizes.append((f"{width}x{height}", width, height))
    if not sizes:
        raise SystemExit("sizes.txt lists no sizes")
    return sizes


def wanted_corpora():
    """From the commit, not the working tree, since that is what gets released."""
    found = sorted(
        line.split("/", 1)[1]
        for line in git("ls-tree", "-d", "--name-only", "HEAD", "corpora/").split()
        if "/" in line
    )
    if not found:
        raise SystemExit("No corpora committed under corpora/")
    return found


def published(tag, repo):
    """Asset names already on that release, or None when there is no release."""
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "assets"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return None
    return {asset["name"] for asset in json.loads(result.stdout)["assets"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args()
    if not args.repo:
        parser.error("Pass --repo owner/name or set GITHUB_REPOSITORY")

    tag = version()
    corpora = wanted_corpora()
    existing = published(tag, args.repo)
    create = existing is None
    if create:
        existing = set()

    data = [name for name in corpora if f"{name}.tar.gz" not in existing]
    print(f"{tag}: {'new release' if create else 'existing release'}")
    print(f"metafiles: {len(corpora) - len(data)}/{len(corpora)} published"
          + (f", missing {', '.join(data)}" if data else ""))

    matrix = []
    for size, width, height in wanted_sizes():
        missing = [name for name in corpora if f"{name}-{size}.tar.gz" not in existing]
        print(f"{size}: {len(corpora) - len(missing)}/{len(corpora)} published"
              + (f", missing {', '.join(missing)}" if missing else ""))
        if missing:
            matrix.append({
                "size": size,
                "width": width,
                "height": height,
                "corpora": ",".join(missing),
                # actions/checkout takes sparse patterns one per line.
                "sparse": "\n".join(["scripts", "sizes.txt"] + [f"corpora/{n}" for n in missing]),
            })

    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"version={tag}\n")
            stream.write(f"create={str(create).lower()}\n")
            stream.write(f"data={json.dumps(data)}\n")
            stream.write(f"matrix={json.dumps(matrix)}\n")

    print(f"{len(data)} metafile archive(s) and {len(matrix)} render job(s) to run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
