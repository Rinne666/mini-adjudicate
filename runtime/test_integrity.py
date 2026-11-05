#!/usr/bin/env python3
"""Payload coverage and non-blocking session warning regressions."""

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_skill_loaded as integrity
import session_start_check


class IntegrityTests(unittest.TestCase):
    def test_refresh_covers_runtime_and_detects_new_or_changed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in integrity.PAYLOAD_FILES:
                (root / name).write_text("payload\n")
            for name in integrity.PAYLOAD_DIRS:
                (root / name).mkdir()
            module = root / "runtime/validator.py"
            module.write_text("print('original')\n")
            manifest = root / "runtime/skill_manifest.json"
            manifest.write_text(json.dumps({"files": {"SKILL.md": "0" * 64}}))
            cache = root / "runtime/__pycache__"
            cache.mkdir()
            (cache / "validator.pyc").write_bytes(b"cache bytes")
            with patch.object(integrity, "REPO_ROOT", root), patch.object(integrity, "MANIFEST_PATH", manifest), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(integrity.refresh(), 0)
                self.assertEqual(integrity.check(), 0)
                files = json.loads(manifest.read_text())["files"]
                self.assertIn("runtime/validator.py", files)
                self.assertFalse(any("__pycache__" in name for name in files))
                module.write_text("print('changed')\n")
                self.assertEqual(integrity.check(), 1)
                integrity.refresh()
                (root / "runtime/new_validator.py").write_text("pass\n")
                self.assertEqual(integrity.check(), 1)

    def test_session_hook_returns_warning_when_integrity_check_times_out(self):
        output = io.StringIO()
        with patch.object(session_start_check.subprocess, "run", side_effect=subprocess.TimeoutExpired("check", 30)), contextlib.redirect_stdout(output):
            self.assertEqual(session_start_check.main(), 0)
        warning = json.loads(output.getvalue())
        self.assertIn("unavailable", warning["additionalContext"])


if __name__ == "__main__":
    unittest.main()
