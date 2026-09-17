"""Missing-only native PNG generation; no per-file metadata or test suite."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ROOT / "corpora"
PLACEABLE_MAGIC = bytes.fromhex("d7cdc69a")


def missing():
    return sorted(
        path for path in CORPORA.rglob("*")
        if path.is_file() and path.suffix.lower() == ".wmf"
        and not path.with_suffix(".png").is_file()
    )


def render_one(path, oracle):
    spec = importlib.util.spec_from_file_location("windows_wmf_render", oracle)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = path.read_bytes()
    if source.startswith(PLACEABLE_MAGIC):
        source = source[22:]
    image = module.render_wmf(source, 128, 128)
    temporary = path.with_suffix(".png.part")
    image.save(temporary, format="PNG")
    temporary.replace(path.with_suffix(".png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Linux-safe missing-reference preflight")
    parser.add_argument("--max-files", type=int, default=200)
    parser.add_argument("--oracle", type=Path, default=ROOT / ".oracle/scripts/windows_wmf_render.py")
    parser.add_argument("--file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.max_files <= 1000:
        parser.error("--max-files must be between 1 and 1000")
    if args.check:
        count = len(missing())
        print(f"{count} missing PNGs")
        if output := os.environ.get("GITHUB_OUTPUT"):
            with open(output, "a", encoding="utf-8") as stream:
                stream.write(f"missing={str(bool(count)).lower()}\n")
        return 0
    if os.name != "nt":
        parser.error("Native reference generation requires Windows")
    if not args.oracle.is_file():
        parser.error("Missing oracle; pass --oracle pointing to windows_wmf_render.py")
    if args.file:
        render_one(args.file, args.oracle)
        return 0

    paths = missing()[:args.max_files]
    deadline = time.monotonic() + 300
    rendered = failed = 0
    for path in paths:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("Batch time limit reached; remaining files are left for another run")
            break
        name = path.relative_to(ROOT).as_posix()
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--file", str(path), "--oracle", str(args.oracle.resolve())],
                capture_output=True, text=True, errors="replace", timeout=min(15, remaining), check=False,
            )
            if result.returncode or not path.with_suffix(".png").is_file():
                detail = (result.stderr or result.stdout).strip().splitlines()
                print(f"failed: {name}: {detail[-1] if detail else f'exit {result.returncode}'}", flush=True)
                failed += 1
            else:
                print(f"rendered: {name}", flush=True)
                rendered += 1
        except subprocess.TimeoutExpired:
            print(f"failed: {name}: timeout", flush=True)
            failed += 1
        finally:
            path.with_suffix(".png.part").unlink(missing_ok=True)
    print(f"{rendered} rendered, {failed} failed, {len(missing())} still missing")
    # Individual native failures must not prevent committing successful PNGs.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
