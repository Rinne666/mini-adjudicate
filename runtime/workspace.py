#!/usr/bin/env python3
"""Initialize adjudication notes and render their tables from canonical JSON.

Only the marked views region is rewritten. Analysis outside it and the JSON
itself remain byte-for-byte intact. This renders recorded facts; it does not
adjudicate claims or make an incomplete workspace ready for delivery.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path

STATE_START = "<!-- adjudication:state:start -->"
STATE_END = "<!-- adjudication:state:end -->"
VIEWS_START = "<!-- adjudication:views:start -->"
VIEWS_END = "<!-- adjudication:views:end -->"
KINDS = ("open_source", "closed_product", "web_service")
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _region(text: str, start: str, end: str) -> tuple[int, int]:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"expected exactly one {start} and {end}; use an init workspace")
    left = text.index(start) + len(start)
    right = text.index(end)
    if left > right:
        raise ValueError(f"reversed markers: {start} / {end}")
    return left, right


def read_state(text: str) -> dict:
    left, right = _region(text, STATE_START, STATE_END)
    match = re.fullmatch(r"\s*```json[ \t]*\r?\n(.*?)\r?\n```\s*", text[left:right], re.DOTALL)
    if not match:
        raise ValueError("state region must contain one fenced json object")
    state = json.loads(match.group(1))
    if not isinstance(state, dict) or not isinstance(state.get("claims"), list):
        raise ValueError("state must be an object with a claims array")
    return state


def _obj(value: object) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("a recorded object has an invalid type; correct the JSON before rendering")
    return value


def _rows(value: object) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("a recorded row list has an invalid type; correct the JSON before rendering")
    return value


def _cell(value: object) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    value = html.escape(str(value), quote=False)
    for char in ("\\", "|", "`", "*", "_", "[", "]"):
        value = value.replace(char, "\\" + char)
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _table(title: str, headers: list[str], rows: list[list[object]]) -> str:
    body = f"## {title}\n\n"
    if not rows:
        return body + "No entries recorded.\n"
    body += "| " + " | ".join(headers) + " |\n"
    body += "| " + " | ".join("---" for _ in headers) + " |\n"
    return body + "".join("| " + " | ".join(_cell(cell) for cell in row) + " |\n" for row in rows)


def render_views(state: dict) -> str:
    claims = _rows(state.get("claims"))
    target = _obj(state.get("target"))
    policy = _obj(target.get("security_policy"))
    channel = _obj(state.get("channel"))
    sections = [
        "> Generated from the Adjudication Table JSON. Edit that JSON, then run render.\n",
        _table("Target and Source Ref", ["Target", "Kind", "Policy source", "Policy reference", "Preferred channel"],
               [[target.get("name"), target.get("kind"), policy.get("source"), policy.get("ref"), target.get("preferred_channel")]]),
        _table("Claims Under Adjudication", ["ID", "Claim", "Origin", "Source revision"],
               [[c.get("id"), c.get("claim"), c.get("claim_source"), c.get("source_ref")] for c in claims]),
    ]
    assertions = [(c, a) for c in claims for a in _rows(c.get("assertions"))]
    sections.append(_table("Claim Decomposition", ["Claim", "Assertion", "Type", "Statement", "Anchor"],
                           [[c.get("id"), a.get("id"), a.get("type"), a.get("statement"), a.get("anchor")] for c, a in assertions]))
    sections.append(_table("Assertion Ledger", ["Claim", "Assertion", "Verdict", "Refutation attempted", "Evidence"],
                           [[c.get("id"), a.get("id"), a.get("verdict"), a.get("refutation_attempted"), a.get("evidence_ids")] for c, a in assertions]))
    assessments = [(c, _obj(c["acceptance"])) for c in claims if c.get("acceptance") is not None]
    sections.append(_table("Acceptance Answers", ["Claim", "Premise", "Boundary", "Divergence", "Acceptability", "Rationale", "Blocking facts", "Evidence"],
                           [[c.get("id"), a.get("premise_kind"), a.get("boundary_state"), a.get("divergence_state"), a.get("acceptability"), a.get("rationale"), a.get("blocking_facts"), a.get("evidence_ids")] for c, a in assessments]))
    oss_rows = []
    for c, a in assessments:
        if a.get("oss_verification") is None:
            continue
        oss = _obj(a["oss_verification"])
        timeline = _obj(oss.get("commit_timeline"))
        history = [f"{h.get('ref', '')}: {h.get('classification', '')}" for h in _rows(oss.get("historical_similar"))]
        oss_rows.append([c.get("id"), oss.get("policy_verified"), timeline.get("introducing_commit"), timeline.get("released_in"), timeline.get("fix_state"), timeline.get("published_as"), history, oss.get("maintainer_preference"), oss.get("evidence_ids")])
    sections.append(_table("OSS Verification", ["Claim", "Policy check", "Introducing commit", "Released in", "Fix state", "Published as", "Similar issues", "Maintainer preference", "Evidence"], oss_rows))
    sections.append(_table("Verdict Table", ["Claim", "Validity", "Acceptability", "Subject", "Action", "Artifact"],
                           [[c.get("id"), c.get("validity"), _obj(c.get("acceptance")).get("acceptability"), c.get("subject"), c.get("action"), c.get("artifact")] for c in claims]))
    reporting_claims = [c for c in claims if c.get("action") in {"report", "rewrite_then_report"}]
    # Keep the proposed delivery order from the JSON claim order even
    # when the reader-facing table is sorted by harm. Blocked claims do
    # not consume a delivery position.
    reportable = [(index + 1, c, _obj(c.get("submission"))) for index, c in enumerate(reporting_claims)]
    reportable.sort(key=lambda row: SEVERITY_ORDER.get(str(row[2].get("severity")), 99))
    submissions = []
    for order, c, sub in reportable:
        core = _obj(sub.get("core_business"))
        awareness = _obj(sub.get("developer_awareness"))
        config = _obj(sub.get("trigger_configuration"))
        boundary = _obj(sub.get("boundary_crossed"))
        targets = [f"{t.get('target', '')} ({t.get('fit', '')}): {t.get('reason', '')}" for t in _rows(sub.get("targets"))]
        submissions.append([order, c.get("id"), sub.get("severity"), f"{core.get('in_core', '')}: {core.get('evidence', '')}", f"{awareness.get('aware', '')}: {awareness.get('evidence', '')}", f"{config.get('special_config_required', '')}: {config.get('default_configuration', '')}; {config.get('evidence', '')}", f"{boundary.get('from', '')} → {boundary.get('to', '')}", targets])
    sections.append(_table("Submission Summary", ["Order", "Claim", "Severity", "Core business", "Developer awareness", "Special configuration", "Boundary crossed", "Targets and reasons"], submissions))
    sections.append(_table("Work Queue", ["ID", "Category", "Task", "Priority", "Reason", "Budget", "Stop condition", "Status", "Outcome", "Evidence"],
                           [[w.get(k) for k in ("id", "category", "task", "priority", "reason", "budget_unit", "stop_condition", "status", "outcome", "evidence_ids")] for w in _rows(state.get("work_queue"))]))
    sections.append(_table("Refutations Considered and Rejected", ["Claim", "Assertion", "Attempt and result", "Verdict", "Evidence"],
                           [[c.get("id"), a.get("id"), a.get("refutation_attempted"), a.get("verdict"), a.get("evidence_ids")] for c, a in assertions]))
    sections.append(_table("Delivery Plan", ["Channel", "Reason", "Alternative considered"], [[channel.get("name"), channel.get("reason"), channel.get("alternative_considered")]]))
    return "\n".join(sections).rstrip() + "\n"


def rendered_text(text: str) -> str:
    state = read_state(text)
    left, right = _region(text, VIEWS_START, VIEWS_END)
    state_left, state_right = _region(text, STATE_START, STATE_END)
    if not (right < state_left or state_right < left):
        raise ValueError("state and views regions must not overlap")
    return text[:left] + "\n\n" + render_views(state) + "\n" + text[right:]


def check_rendered(text: str) -> list[str]:
    """Legacy notes have no generated region; marked notes must stay in sync."""
    if not any(marker in text for marker in (STATE_START, STATE_END, VIEWS_START, VIEWS_END)):
        return []
    try:
        expected = rendered_text(text)
    except (ValueError, TypeError) as exc:
        return [f"generated notes: {exc}"]
    if expected != text:
        return ["generated tables differ from the JSON state; run workspace.py render <notes>"]
    return []


def initial_notes(target: str, kind: str, source_ref: str, claims: list[str]) -> str:
    state = {
        "target": {"name": target, "kind": kind, "security_policy": {"source": "none", "ref": ""}, "preferred_channel": ""},
        "claims": [{"id": f"C{i + 1}", "claim": claim, "claim_source": "provided at intake", "source_ref": source_ref, "assertions": [], "evidence_ids": []} for i, claim in enumerate(claims)],
        "coverage_paragraph_present": True,
        "work_queue": [],
        "channel": {"name": "", "reason": ""},
    }
    state_json = json.dumps(state, ensure_ascii=False, indent=2)
    text = (
        f"# Adjudication Notes — {_cell(target)}\n\n"
        "This is an incomplete workspace. Record evidence and verdicts before delivery.\n\n"
        "## Analysis\n\n"
        f"Source revision to adjudicate: {_cell(source_ref)}.\n\n"
        "Keep narrative reasoning here; render preserves everything outside its marked views.\n\n"
        "## Policy Sources\n\n"
        "Record source_url, checked_at, program_scope, and the claim each live rule applies to.\n\n"
        "## Adjudication Table\n\n"
        f"{STATE_START}\n```json\n{state_json}\n```\n{STATE_END}\n\n"
        f"{VIEWS_START}\n{VIEWS_END}\n"
    )
    return rendered_text(text)


def _replace_file(path: Path, content: str) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="create incomplete notes and an evidence ledger without overwriting existing files")
    init.add_argument("notes", type=Path)
    init.add_argument("--target", required=True)
    init.add_argument("--kind", choices=KINDS, default="open_source")
    init.add_argument("--source-ref", default="")
    init.add_argument("--claim", action="append", default=[], help="claim from the completed audit; repeat for multiple claims")
    render = subparsers.add_parser("render", help="refresh generated tables, preserving JSON and manual analysis")
    render.add_argument("notes", type=Path)
    render.add_argument("--check", action="store_true", help="exit 1 if generated tables are stale, without writing")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if not args.target.strip() or any(not claim.strip() for claim in args.claim):
                raise ValueError("target and supplied claims must not be empty")
            content = initial_notes(args.target, args.kind, args.source_ref, args.claim)
            args.notes.parent.mkdir(parents=True, exist_ok=True)
            with args.notes.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
            (args.notes.parent / "evidence").mkdir(exist_ok=True)
            ledger = args.notes.parent / "evidence.jsonl"
            if not ledger.exists():
                ledger.touch(exist_ok=False)
            print(f"Created {args.notes}; incomplete until the adjudication gates pass.")
        else:
            with args.notes.open(encoding="utf-8", newline="") as stream:
                text = stream.read()
            updated = rendered_text(text)
            if args.check and updated != text:
                print("FAIL: generated tables differ from the JSON state; run render without --check", file=sys.stderr)
                return 1
            if not args.check and updated != text:
                _replace_file(args.notes, updated)
            print(f"OK: generated tables {'match' if args.check else 'rendered from'} the JSON state")
    except (OSError, ValueError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
