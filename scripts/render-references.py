"""Render corpora at one output size and package each as a tar.gz.

Renders run in worker subprocesses because a malformed metafile can take GDI down
with it. Workers report each file as they finish, so the first file a dead worker
never reported is the one that killed it. That file is retried alone and the rest
of its chunk carries on in bulk.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ROOT / "corpora"
PLACEABLE_MAGIC = bytes.fromhex("d7cdc69a")
PLACEABLE_HEADER = 22
CHUNK = 200


def select_corpora(selection):
    available = sorted(p.name for p in CORPORA.iterdir() if p.is_dir()) if CORPORA.is_dir() else []
    if not selection or selection.strip().lower() == "all":
        return available
    chosen = [name.strip() for name in selection.split(",") if name.strip()]
    unknown = [name for name in chosen if name not in available]
    if unknown:
        raise ValueError(
            f"Unknown corpora {', '.join(unknown)}; available: {', '.join(available) or 'none'}"
        )
    return chosen


def sources(corpus):
    root = CORPORA / corpus
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".wmf")


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("windows_wmf_render", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_one(module, source, target, width, height):
    data = source.read_bytes()
    if data.startswith(PLACEABLE_MAGIC):
        data = data[PLACEABLE_HEADER:]
    image = module.render_wmf(data, width, height)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".png.part")
    try:
        image.save(partial, format="PNG")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def run_worker(spec, oracle, width, height):
    module = load_oracle(oracle)
    for line in Path(spec).read_text(encoding="utf-8").splitlines():
        index, source, target = json.loads(line)
        try:
            render_one(module, Path(source), Path(target), width, height)
            print(json.dumps([index, ""]), flush=True)
        except Exception as error:  # noqa: BLE001 - the oracle raises whatever GDI does
            print(json.dumps([index, f"{type(error).__name__}: {error}"]), flush=True)
    return 0


def render_chunk(items, oracle, width, height):
    """Render items in one subprocess, returning {index: "" or why it did not render}."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as handle:
        for index, source, target in items:
            handle.write(json.dumps([index, str(source), str(target)]) + "\n")
        spec = Path(handle.name)

    try:
        result = subprocess.run(
            [
                sys.executable, str(Path(__file__).resolve()), "--worker", str(spec),
                "--oracle", str(oracle), "--width", str(width), "--height", str(height),
            ],
            capture_output=True, text=True, errors="replace", check=False,
        )
    finally:
        spec.unlink(missing_ok=True)

    results = {}
    for line in result.stdout.splitlines():
        try:
            index, error = json.loads(line)
        except (ValueError, TypeError):
            continue
        results[index] = error

    unreported = [item for item in items if item[0] not in results]
    if not unreported:
        return results

    if len(items) == 1:
        tail = (result.stderr or result.stdout).strip().splitlines()
        results[items[0][0]] = tail[-1] if tail else f"worker exit {result.returncode}"
        return results

    results.update(render_chunk(unreported[:1], oracle, width, height))
    if unreported[1:]:
        results.update(render_chunk(unreported[1:], oracle, width, height))
    return results


def render_corpus(corpus, oracle, width, height, outdir, label):
    files = sources(corpus)
    staging = outdir / corpus
    shutil.rmtree(staging, ignore_errors=True)
    items = [
        (index, source, staging / source.relative_to(CORPORA / corpus).with_suffix(".png"))
        for index, source in enumerate(files)
    ]

    results = {}
    for start in range(0, len(items), CHUNK):
        results.update(render_chunk(items[start:start + CHUNK], oracle, width, height))
        print(f"{corpus}: {min(start + CHUNK, len(items))}/{len(items)}", flush=True)

    for index, source, _ in items:
        error = results.get(index, "no result")
        if error:
            print(f"  no reference for {source.relative_to(CORPORA)}: {error}", flush=True)

    staging.mkdir(parents=True, exist_ok=True)
    archive = outdir / f"{corpus}-{label}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        # Size first, so archives for different sizes unpack side by side into one
        # cache directory instead of overwriting each other.
        tar.add(staging, arcname=f"{label}/{corpus}")

    rendered = sum(1 for error in results.values() if not error)
    print(f"{corpus}: {rendered:,}/{len(items):,} -> {archive.name}", flush=True)
    return rendered, len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--height", type=int, default=128)
    parser.add_argument("--corpus", default="", help="comma-separated names; blank renders all")
    parser.add_argument("--out", type=Path, default=ROOT / "build")
    parser.add_argument("--oracle", type=Path, default=ROOT / ".oracle/scripts/windows_wmf_render.py")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args()

    width, height = args.width, args.height
    if width < 1 or height < 1:
        parser.error(f"Dimensions must be positive, got {width}x{height}")

    if args.worker:
        return run_worker(args.worker, args.oracle, width, height)

    if os.name != "nt":
        parser.error("Rendering references needs Windows")
    if not args.oracle.is_file():
        parser.error(f"No oracle at {args.oracle}; pass --oracle pointing at windows_wmf_render.py")
    try:
        # Fail here rather than letting every worker die on the same import.
        load_oracle(args.oracle)
    except Exception as error:  # noqa: BLE001 - report whatever the import raised
        parser.error(f"Oracle at {args.oracle} will not import: {error}")
    try:
        chosen = select_corpora(args.corpus)
    except ValueError as error:
        parser.error(str(error))
    if not chosen:
        parser.error("No corpora found under corpora/")

    label = f"{width}x{height}"
    args.out.mkdir(parents=True, exist_ok=True)
    rendered = total = 0
    for corpus in chosen:
        done, count = render_corpus(corpus, args.oracle.resolve(), width, height, args.out, label)
        rendered += done
        total += count

    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"size={label}\n")

    print(f"{rendered:,}/{total:,} rendered at {label}")
    # A metafile GDI will not draw has no reference. That is not a failed run.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
