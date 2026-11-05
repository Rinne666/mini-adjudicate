#!/usr/bin/env python3
"""Portable source capture and source-snapshot regression checks."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import validate_adjudication as va

SCRIPT = Path(__file__).resolve().parent / "evidence_log.py"


class EvidenceLogTests(unittest.TestCase):
    def capture(self, root, operation, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), operation, "--ledger", "review/evidence.jsonl", "--artifact-dir", "review/evidence", *args],
            cwd=root, capture_output=True, text=True,
        )

    def test_relative_capture_moves_with_workspace_and_records_source_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "original workspace"
            root.mkdir()
            source = root / "source file.txt"
            source.write_bytes(b"first line\nsecond line\n")
            result = self.capture(root, "read", "--path", source.name, "--start", "1", "--end", "2")
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = root / "review/evidence.jsonl"
            record = json.loads(ledger.read_text())
            self.assertEqual(record["artifact"], "evidence/E000001.txt")
            self.assertEqual(record["cwd"], "..")
            self.assertEqual(record["path"], "source file.txt")
            self.assertEqual(record["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            moved = Path(directory) / "moved workspace"
            shutil.copytree(root, moved)
            _, errors = va._load_evidence_ledger(str(moved / "review/evidence.jsonl"))
            self.assertEqual(errors, [])
            (moved / source.name).write_bytes(b"changed source\n")
            _, errors = va._load_evidence_ledger(str(moved / "review/evidence.jsonl"))
            self.assertTrue(errors, "a read from another source snapshot must not silently validate")

    def test_read_beyond_eof_cannot_be_cited_as_a_source_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_text("one line\n")
            result = self.capture(root, "read", "--path", "source.txt", "--start", "50", "--end", "60")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "review/evidence.jsonl").exists())

    def test_absence_search_is_replayed_after_relocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "original"
            root.mkdir()
            (root / "source.txt").write_text("class Example {}\n")
            result = self.capture(root, "search", "--pattern", r"class\s+Guard", "source.txt")
            self.assertEqual(result.returncode, 0, result.stderr)
            moved = Path(directory) / "moved"
            shutil.copytree(root, moved)
            _, errors = va._load_evidence_ledger(str(moved / "review/evidence.jsonl"))
            self.assertEqual(errors, [])
            (moved / "source.txt").write_text("class Guard {}\n")
            _, errors = va._load_evidence_ledger(str(moved / "review/evidence.jsonl"))
            self.assertTrue(any("no longer reproduces" in e for e in errors), errors)

    def test_parallel_capture_does_not_reuse_ids_or_overwrite_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_text("".join(f"line {i}\n" for i in range(1, 10001)))
            artifact_dir = root / "review/evidence"
            artifact_dir.mkdir(parents=True)
            # Simulate an interrupted capture whose artifact must survive.
            orphan = artifact_dir / "E000001.txt"
            orphan.write_text("preserve orphan\n")
            processes = [subprocess.Popen(
                [sys.executable, str(SCRIPT), "read", "--ledger", "review/evidence.jsonl", "--artifact-dir", "review/evidence", "--path", "source.txt", "--start", str(i), "--end", str(i)],
                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) for i in range(1, 5)]
            for process in processes:
                _, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stderr)
            records, errors = va._load_evidence_ledger(str(root / "review/evidence.jsonl"))
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 4)
            self.assertEqual(set(records), {"E000002", "E000003", "E000004", "E000005"})
            captures = [(root / "review" / record["artifact"]).read_text() for record in records.values()]
            self.assertEqual(set(captures), {f"{i}: line {i}\n" for i in range(1, 5)})
            self.assertEqual(orphan.read_text(), "preserve orphan\n")
            self.assertFalse((root / "review/evidence.jsonl.lock").exists())


if __name__ == "__main__":
    unittest.main()
