#!/usr/bin/env python3
"""Check the installed skill payload against its checked-in file manifest.

This verifies local file integrity, including runtime code and fixtures. It
does not inspect the agent's context, establish which instructions it read,
or compare the package with a remote repository or Git HEAD.

Two modes:

  --refresh   Discover payload files, compute sha256, and write the manifest.

  (no flag)   Walk the repo, compute sha256 for every file, and
              compare against runtime/skill_manifest.json. Exit
              non-zero on mismatch.

Usage in a session-start hook:

    python runtime/check_skill_loaded.py
    if [ $? -ne 0 ]; then
        echo "skill stale; reloading"; exit 1
    fi

Exit codes:

    0  -- every file matches the manifest.
    1  -- at least one file is missing or hash mismatches.
    2  -- manifest itself is missing or malformed.

This script is intentionally stdlib-only and makes no network
calls. It compares against a checked-in manifest, not a remote
source of truth, so the comparison is hermetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent / "skill_manifest.json"
REPO_ROOT = MANIFEST_PATH.resolve().parent.parent
PAYLOAD_FILES = ("SKILL.md", "README.md", "_meta.json", "package.json")
PAYLOAD_DIRS = ("bin", "cli", "skills", "references", "templates", "schemas", "runtime", "fixtures")


def _payload_files() -> set[str]:
    paths = set(PAYLOAD_FILES)
    for directory in PAYLOAD_DIRS:
        for path in (REPO_ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            if path.resolve() == MANIFEST_PATH.resolve():
                continue
            paths.add(path.relative_to(REPO_ROOT).as_posix())
    return paths


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest missing at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: manifest malformed: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        print("FAIL: manifest has no 'files' dict", file=sys.stderr)
        sys.exit(2)
    return manifest


def refresh() -> int:
    manifest = _load_manifest()
    new_files: dict[str, str] = {}
    for relpath in sorted(_payload_files()):
        path = REPO_ROOT / relpath
        if not path.exists():
            print(f"FAIL: file missing during refresh: {relpath}", file=sys.stderr)
            return 1
        new_files[relpath] = _sha256(path)
    manifest["files"] = new_files
    manifest["_comment"] = "Hashes of the local installed payload. This checks file integrity, not agent context or remote freshness. Regenerate with runtime/check_skill_loaded.py --refresh after reviewed edits."
    import time
    manifest["generated_at_unix"] = int(time.time())
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: refreshed {len(new_files)} files in {MANIFEST_PATH}")
    return 0


def check() -> int:
    manifest = _load_manifest()
    failures: list[str] = []
    expected_paths = _payload_files()
    for relpath in sorted(expected_paths - manifest["files"].keys()):
        failures.append(f"{relpath}: payload file is not covered by the manifest")
    for relpath in sorted(manifest["files"].keys() - expected_paths):
        failures.append(f"{relpath}: manifest entry is outside the current payload")
    for relpath, expected in manifest["files"].items():
        if relpath not in expected_paths:
            continue
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            failures.append(f"{relpath}: manifest has invalid hash; run --refresh after reviewing files")
            continue
        path = REPO_ROOT / relpath
        if not path.is_file():
            failures.append(f"{relpath}: file missing")
            continue
        actual = _sha256(path)
        if actual != expected:
            failures.append(f"{relpath}: hash mismatch (manifest={expected[:12]}... actual={actual[:12]}...)")
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        print(f"FAIL: {len(failures)} file(s) stale; re-run --refresh and reload", file=sys.stderr)
        return 1
    print(f"OK: {len(manifest['files'])} file(s) match manifest")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that local skill payload files match the checked-in manifest.")
    parser.add_argument("--refresh", action="store_true", help="Recompute hashes for every tracked file and update the manifest.")
    args = parser.parse_args(argv)
    if args.refresh:
        return refresh()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
