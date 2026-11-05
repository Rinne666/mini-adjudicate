#!/usr/bin/env python3
"""Behavioral checks for canonical state and generated adjudication views."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import workspace as ws
import validate_adjudication as va

SCRIPT = Path(ws.__file__).resolve()
FIXTURE = SCRIPT.parent.parent / "fixtures/mini-adjudication/expected/adjudication-notes.md"


class WorkspaceTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def replace_state(self, text, state):
        left = text.index(ws.STATE_START) + len(ws.STATE_START)
        right = text.index(ws.STATE_END)
        return text[:left] + "\n```json\n" + json.dumps(state, indent=2) + "\n```\n" + text[right:]

    def test_init_preserves_intake_without_inventing_a_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "space dir/adjudication-test.md"
            result = self.command("init", notes, "--target", "Example", "--source-ref", "abc123", "--claim", "The login path skips a check")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = notes.read_text()
            state = ws.read_state(text)
            self.assertEqual(state["claims"][0]["source_ref"], "abc123")
            self.assertNotIn("validity", state["claims"][0])
            self.assertEqual(ws.check_rendered(text), [])
            self.assertNotEqual(va.validate(text, {})[0], 0)
            self.assertTrue((notes.parent / "evidence.jsonl").is_file())
            self.assertTrue((notes.parent / "evidence").is_dir())
            before = notes.read_bytes()
            again = self.command("init", notes, "--target", "Replacement")
            self.assertEqual(again.returncode, 2)
            self.assertEqual(notes.read_bytes(), before)

    def test_render_is_idempotent_and_preserves_json_and_analysis(self):
        text = ws.initial_notes("Example", "open_source", "rev-1", ["Original claim"])
        text += "\n## Independent analysis\n\nKeep **this** text exactly.\r\n"
        state = ws.read_state(text)
        state["claims"][0]["claim"] = "Updated | claim\n<script>alert(1)</script>"
        edited = self.replace_state(text, state)
        rendered = ws.rendered_text(edited)
        self.assertEqual(ws.read_state(rendered), state)
        self.assertTrue(rendered.endswith("Keep **this** text exactly.\r\n"))
        self.assertEqual(rendered[:rendered.index(ws.VIEWS_START)], edited[:edited.index(ws.VIEWS_START)])
        self.assertEqual(ws.rendered_text(rendered), rendered)
        views = rendered.split(ws.VIEWS_START)[1].split(ws.VIEWS_END)[0]
        self.assertIn("Updated \\| claim<br>&lt;script&gt;", views)
        self.assertNotIn("<script>", views)

    def test_check_detects_drift_without_writing_and_render_repairs_it(self):
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "adjudication-example.md"
            text = ws.initial_notes("Example", "closed_product", "rev-1", ["Original claim"])
            state = ws.read_state(text)
            state["claims"][0]["claim"] = "Revised claim"
            notes.write_text(self.replace_state(text, state))
            before = notes.read_bytes()
            self.assertEqual(self.command("render", notes, "--check").returncode, 1)
            self.assertEqual(notes.read_bytes(), before)
            self.assertEqual(self.command("render", notes).returncode, 0)
            self.assertEqual(self.command("render", notes, "--check").returncode, 0)
            self.assertIn("Revised claim", notes.read_text().split(ws.VIEWS_START)[1])

    def test_legacy_or_broken_markers_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "adjudication-legacy.md"
            for text in ("# My manual report\n", ws.initial_notes("Example", "open_source", "", []).replace(ws.VIEWS_END, "")):
                notes.write_text(text)
                before = notes.read_bytes()
                self.assertEqual(self.command("render", notes).returncode, 2)
                self.assertEqual(notes.read_bytes(), before)

    def test_summary_orders_severity_and_keeps_pending_out_of_report_list(self):
        state, err = va._extract_adjudication_table(FIXTURE.read_text())
        self.assertIsNone(err)
        high = state["claims"][0]
        low = json.loads(json.dumps(high))
        low["id"] = "LOW-CLAIM"
        low["submission"]["severity"] = "low"
        high["id"] = "HIGH-CLAIM"
        pending = json.loads(json.dumps(high))
        pending.update(id="PENDING-CLAIM", action="needs_evidence")
        pending["acceptance"] = {"premise_kind": "unknown", "acceptability": "pending", "blocking_facts": ["Observe deployment setting"], "rationale": "Unknown setting", "evidence_ids": ["E000001"]}
        state["claims"] = [low, pending, high]
        views = ws.render_views(state)
        summary = views.split("## Submission Summary")[1].split("## Work Queue")[0]
        self.assertLess(summary.index("HIGH-CLAIM"), summary.index("LOW-CLAIM"))
        self.assertIn("| 2 | HIGH-CLAIM |", summary)
        self.assertIn("| 1 | LOW-CLAIM |", summary)
        self.assertNotIn("PENDING-CLAIM", summary)
        self.assertIn("Observe deployment setting", views)
        self.assertIn("declared-invariant rule", views.split("## OSS Verification")[1].split("## Verdict Table")[0])

    def test_delivery_requires_current_views_and_uses_the_marked_state(self):
        fixture_state, error = va._extract_adjudication_table(FIXTURE.read_text())
        self.assertIsNone(error)
        text = ws.initial_notes("Example", "open_source", "", [])
        text = self.replace_state(text, fixture_state)
        # An exploratory JSON example must not become the canonical state.
        text = '```json\n{"claims": []}\n```\n\n' + text
        records, errors = va._load_evidence_ledger(str(FIXTURE.parent / "evidence.jsonl"))
        self.assertEqual(errors, [])
        self.assertEqual(va.validate(text, records)[0], 1)
        rendered = ws.rendered_text(text)
        code, errors = va.validate(rendered, records)
        self.assertEqual(code, 0, errors)
        left = rendered.index(ws.VIEWS_START)
        changed = rendered[:left] + rendered[left:].replace("high", "critical", 1)
        code, errors = va.validate(changed, records)
        self.assertEqual(code, 1)
        self.assertTrue(any("generated tables differ" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
