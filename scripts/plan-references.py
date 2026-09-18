"""Work out which corpora have no reference asset yet, and at which sizes.

Sizes come from sizes.txt, corpora from the directories under corpora/, and what
already exists from the releases themselves. Whatever is in the first two and not
the third is the work. Deleting a release puts its corpora back on the list.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ROOT / "corpora"
SIZES = ROOT / "sizes.txt"


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
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "-d", "--name-only", "HEAD", "corpora/"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise SystemExit(f"Cannot list corpora: {result.stderr.strip()}")
    found = sorted(line.split("/", 1)[1] for line in result.stdout.split() if "/" in line)
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

    corpora = wanted_corpora()
    matrix, create = [], []

    for tag, width, height in wanted_sizes():
        existing = published(tag, args.repo)
        if existing is None:
            create.append(tag)
            existing = set()
        missing = [name for name in corpora if f"{name}-{tag}.tar.gz" not in existing]
        print(f"{tag}: {len(corpora) - len(missing)}/{len(corpora)} published"
              + (f", missing {', '.join(missing)}" if missing else ""))
        if missing:
            matrix.append({
                "size": tag,
                "width": width,
                "height": height,
                "corpora": ",".join(missing),
                # actions/checkout takes sparse patterns one per line.
                "sparse": "\n".join(["scripts", "sizes.txt"] + [f"corpora/{n}" for n in missing]),
            })

    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"matrix={json.dumps(matrix)}\n")
            stream.write(f"create={json.dumps(create)}\n")

    print(f"{len(matrix)} job(s) to run, {len(create)} release(s) to open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
