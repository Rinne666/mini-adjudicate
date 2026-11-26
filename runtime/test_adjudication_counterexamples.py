#!/usr/bin/env python3
"""Counter-example tests for validate_adjudication.py.

A validator that only ever sees valid input proves nothing. Each case
here takes the fixture — a correct adjudication — breaks it in exactly
one way, and asserts that the validator rejects the broken version.

The broken versions below are the ways this framework actually fails in
practice:

  * an absence that is asserted but does not reproduce (the ledger says
    "no matches" for a pattern that does match),
  * an unresolved conclusion resting on search evidence with no
    reproducible absence behind it,
  * a verdict asserted rather than derived,
  * a claim that does not hold carrying an acceptance verdict, so a
    non-vulnerability is dressed up as an "unacceptable" one,
  * a "confirmed" assertion backed only by a search,
  * a subject written as a consequence,
  * two copies of the same search counted as two checks,
  * work left open at delivery,
  * a divergence claimed absent without reproducible absence behind it,
  * a reportable claim with no submission block (no core / awareness /
    config / boundary / target answers),
  * a submission without a severity — the summary table is sorted by it,
  * a submission that says special configuration is required while the
    premise says the attacker creates the condition alone,
  * a submission with no primary target — nothing would be submitted,
  * an open-source holding claim with no oss_verification block.

Run: python runtime/test_adjudication_counterexamples.py
Exit codes: 0 all pass, 1 a test failed.
"""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_adjudication import (  # noqa: E402
    _extract_adjudication_table,
    _load_evidence_ledger,
    validate,
)
import validate_adjudication as va

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "fixtures" / "mini-adjudication"
NOTES = FIXTURE / "expected" / "adjudication-notes.md"
LEDGER = FIXTURE / "expected" / "evidence.jsonl"

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"OK:   {label}")
    else:
        print(f"FAIL: {label}{(' — ' + detail) if detail else ''}")
        failures.append(label)


def extract(text: str) -> dict:
    obj, err = _extract_adjudication_table(text)
    if obj is None:
        raise SystemExit(f"fixture notes have no adjudication table: {err}")
    return obj


def rebuild(text: str, obj: dict) -> str:
    """Put a mutated table back into the notes, fences and all."""
    start = text.index("```json")
    close = text.index("```", start + len("```json"))
    body = json.dumps(obj, indent=2, ensure_ascii=False)
    return text[:start] + "```json\n" + body + "\n```" + text[close + 3:]


def claim(obj: dict, claim_id: str) -> dict:
    for entry in obj["claims"]:
        if entry["id"] == claim_id:
            return entry
    raise SystemExit(f"no claim {claim_id}")


def assertion(entry: dict, assertion_id: str) -> dict:
    for item in entry["assertions"]:
        if item["id"] == assertion_id:
            return item
    raise SystemExit(f"no assertion {assertion_id}")


def stage(tmp: Path) -> Path:
    """Copy the fixture into a temp tree so the ledger's relative cwd resolves.

    The ledger records the working directory it was captured in, relative
    to the ledger itself. Re-verifying a recorded search therefore needs
    that directory to exist with the same shape. The temp tree mirrors
    the repository layout so the recorded paths still point at the same
    files.
    """
    target = tmp / "fixtures" / "mini-adjudication"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(FIXTURE, target)
    return target / "expected" / "evidence.jsonl"


def run(notes_text: str, ledger_path: Path) -> list[str]:
    records, ledger_errors = _load_evidence_ledger(str(ledger_path))
    _, errors = validate(notes_text, records)
    return errors + ledger_errors


def expect_rejected(label: str, notes_text: str, ledger_path: Path, needle: str) -> None:
    errors = run(notes_text, ledger_path)
    hit = any(needle in err for err in errors)
    check(label, hit, f"expected an error containing {needle!r}, got {errors!r}")


base_text = NOTES.read_text(encoding="utf-8")

with tempfile.TemporaryDirectory() as raw_tmp:
    tmp = Path(raw_tmp)

    # 0. The fixture itself must pass, or the cases below prove nothing.
    ledger_path = stage(tmp)
    baseline_errors = run(base_text, ledger_path)
    check("the fixture itself is accepted", not baseline_errors, repr(baseline_errors))

    # 1. An absence that does not reproduce.
    #
    # This is the failure the fixture used to have: a ledger entry that
    # claimed "no matches" for a pattern that does match the source. The
    # ledger is self-reported, so nothing but a re-run catches it.
    ledger_path = stage(tmp)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    patched = []
    for line in lines:
        record = json.loads(line)
        if record["id"] == "E000008":
            record["query"] = "getenv"
            record["command"] = [
                "rg", "--line-number", "--with-filename", "--no-heading", "--color",
                "never", "--max-count", "500", "--", "getenv",
                "fixtures/mini-adjudication/app.php",
            ]
        patched.append(json.dumps(record, sort_keys=True))
    ledger_path.write_text("\n".join(patched) + "\n", encoding="utf-8")
    expect_rejected(
        "a zero-match search that no longer reproduces is rejected",
        base_text, ledger_path, "no longer reproduces",
    )

    # 2. An unresolved conclusion resting on search evidence alone.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    entry = claim(obj, "C3")
    item = assertion(entry, "A8")
    item["evidence_ids"] = ["E000010", "E000011"]
    item.pop("absence_searches", None)
    expect_rejected(
        "an unresolved assertion on search evidence alone must show its absence",
        rebuild(base_text, obj), ledger_path, "absence_searches",
    )

    # 3. A verdict asserted rather than derived.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C3")["validity"] = "holds"
    expect_rejected(
        "a validity that does not follow from its assertions is rejected",
        rebuild(base_text, obj), ledger_path, "derive",
    )

    # 4. A claim that does not hold carrying an acceptance verdict.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C2")["acceptance"] = {
        "premise_kind": "attacker_only",
        "boundary_state": "not_declared",
        "divergence_state": "present",
        "acceptability": "accept",
        "rationale": "dressed up",
        "evidence_ids": ["E000004"],
        "divergence_sides": [
            {"file_line": "fixtures/mini-adjudication/app.php:181", "behavior": "a"},
            {"file_line": "fixtures/mini-adjudication/app.php:184", "behavior": "b"},
        ],
    }
    expect_rejected(
        "a claim that does not hold cannot carry an acceptance verdict",
        rebuild(base_text, obj), ledger_path, "must not carry an acceptance verdict",
    )

    # 5. A "confirmed" assertion backed only by a search.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    assertion(claim(obj, "C1"), "A1")["evidence_ids"] = ["E000008"]
    expect_rejected(
        "a confirmed assertion must cite a captured source read",
        rebuild(base_text, obj), ledger_path, "must cite a captured source read",
    )

    # 6. A subject written as a consequence.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["subject"] = "An attacker can take over any account by name."
    expect_rejected(
        "a subject stated as a consequence is rejected",
        rebuild(base_text, obj), ledger_path, "states a consequence, not an invariant",
    )

    # 7. The same search counted twice is not two checks.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    item = assertion(claim(obj, "C3"), "A8")
    item["absence_searches"] = [{"evidence_id": "E000010"}, {"evidence_id": "E000010"}]
    expect_rejected(
        "two copies of one search are not two absence checks",
        rebuild(base_text, obj), ledger_path, "two distinct captured zero-match searches",
    )

    # 8. Work left open at delivery.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    obj["work_queue"][0]["status"] = "active"
    expect_rejected(
        "an open work item blocks delivery",
        rebuild(base_text, obj), ledger_path, "every item must be completed or deferred",
    )

    # 9. A divergence claimed absent with no reproducible absence behind it.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    acceptance = claim(obj, "C1")["acceptance"]
    acceptance["divergence_state"] = "absent"
    acceptance.pop("divergence_sides", None)
    expect_rejected(
        "a divergence claimed absent must show two zero-match searches",
        rebuild(base_text, obj), ledger_path, "divergence_absence_searches",
    )

    # 10. The notes must carry the sections a reviewer scans.
    ledger_path = stage(tmp)
    stripped = re.sub(r"^#{1,4}\s*Assertion Ledger.*$", "", base_text, flags=re.MULTILINE)
    expect_rejected(
        "notes without every coverage section are rejected",
        stripped, ledger_path, "missing coverage section",
    )

    # 11. A reportable claim with no submission block.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1").pop("submission", None)
    expect_rejected(
        "a reportable claim must carry its submission block",
        rebuild(base_text, obj), ledger_path, "submission",
    )

    # 12. A trigger-configuration answer that contradicts the premise.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["submission"]["trigger_configuration"]["special_config_required"] = True
    expect_rejected(
        "special config required + attacker_only premise is rejected",
        rebuild(base_text, obj), ledger_path, "same fact",
    )

    # 13. A submission with no primary target.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    for item in claim(obj, "C1")["submission"]["targets"]:
        if item["fit"] == "primary":
            item["fit"] = "secondary"
    expect_rejected(
        "a submission with no primary target is rejected",
        rebuild(base_text, obj), ledger_path, "exactly one primary target",
    )

    # 14. An open-source holding claim with no oss_verification block.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["acceptance"].pop("oss_verification", None)
    expect_rejected(
        "an open-source holding claim must verify policy, timeline, history, preference",
        rebuild(base_text, obj), ledger_path, "oss_verification",
    )

    # 15. A submission with no severity — the summary table is sorted by it.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["submission"].pop("severity", None)
    expect_rejected(
        "a submission without a severity rating is rejected",
        rebuild(base_text, obj), ledger_path, "submission.severity",
    )

    # 16. Subsumed by existing privilege cannot claim accept/report.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["acceptance"]["privilege_ceiling"]["subsumed_by_existing_privilege"] = True
    expect_rejected(
        "subsumed privilege claiming accept is rejected",
        rebuild(base_text, obj), ledger_path, "derive",
    )

    # 17. Trusted infrastructure channel cannot claim accept/report.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["acceptance"]["privilege_ceiling"]["trusted_infrastructure_channel"] = True
    expect_rejected(
        "trusted infrastructure channel claiming accept is rejected",
        rebuild(base_text, obj), ledger_path, "derive",
    )

    # 18. requires_privileged_or_trusted_channel cannot claim accept.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["acceptance"]["premise_kind"] = "requires_privileged_or_trusted_channel"
    expect_rejected(
        "privileged/trusted-channel premise claiming accept is rejected",
        rebuild(base_text, obj), ledger_path, "derive",
    )

    # 19. security_fix precedent without alignment check is rejected.
    ledger_path = stage(tmp)
    obj = extract(base_text)
    claim(obj, "C1")["acceptance"]["oss_verification"]["historical_similar"][0].pop("transferable", None)
    expect_rejected(
        "security_fix precedent without transferable check is rejected",
        rebuild(base_text, obj), ledger_path, "transferable",
    )

    # The action must be determined by BOTH verdicts, not just validity.
    for verdict, premise, boundary, expected_action in (
        ("decline", "attacker_only", "declared_and_consistent", "hardening_note"),
        ("accept_after_rewrite", "requires_third_party_misconfiguration", "declared_and_violated", "rewrite_then_report"),
    ):
        obj = extract(base_text)
        acceptance = claim(obj, "C1")["acceptance"]
        acceptance.update(acceptability=verdict, premise_kind=premise, boundary_state=boundary)
        expect_rejected(f"{verdict} cannot retain report action", rebuild(base_text, obj), ledger_path, expected_action)

    for missing in ("defect", "reachability", "consequence"):
        obj = extract(base_text)
        entry = claim(obj, "C1")
        entry["assertions"] = [a for a in entry["assertions"] if a["type"] != missing]
        expect_rejected(f"holds requires {missing} coverage", rebuild(base_text, obj), ledger_path, "derive 'needs_more_evidence'")
    obj = extract(base_text)
    entry = claim(obj, "C1")
    entry["assertions"] = [a for a in entry["assertions"] if a["type"] == "precondition"]
    expect_rejected("only an unresolved precondition cannot establish holds", rebuild(base_text, obj), ledger_path, "derive 'needs_more_evidence'")

    for field, value in (("id", ""), ("source_ref", 123), ("unknown_key", True), ("validity", [])):
        obj = extract(base_text)
        claim(obj, "C1")[field] = value
        expect_rejected(f"schema rejects malformed {field}", rebuild(base_text, obj), ledger_path, field)

    # Pending is a deliverable blocking explanation, never a report.
    pending = extract(base_text)
    entry = claim(pending, "C1")
    entry["acceptance"] = {
        "premise_kind": "unknown", "acceptability": "pending",
        "blocking_facts": ["Whether the deployed extension can return an empty response"],
        "rationale": "The source proves the defect but does not establish control of its trigger.",
        "evidence_ids": ["E000001"],
    }
    entry["action"] = "needs_evidence"
    entry.pop("submission")
    pending_text = rebuild(base_text, pending)
    check("pending can deliver a blocking explanation without divergence or OSS conclusions", not run(pending_text, ledger_path))
    entry["action"] = "report"
    expect_rejected("pending cannot be reported", rebuild(base_text, pending), ledger_path, "needs_evidence")
    entry["action"] = "needs_evidence"
    for facts in ([], [" "], [123]):
        entry["acceptance"]["blocking_facts"] = facts
        expect_rejected("pending must identify concrete missing facts", rebuild(base_text, pending), ledger_path, "blocking_facts")
    entry["acceptance"]["blocking_facts"] = ["The trigger's controller remains unknown"]
    entry["acceptance"]["premise_kind"] = "attacker_only"
    expect_rejected("known premise cannot claim pending", rebuild(base_text, pending), ledger_path, "pending requires")

    # Every caller using loaded evidence receives its integrity failures.
    ledger_path = stage(tmp)
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    for row in rows:
        row["artifact"] = row["artifact"].replace("/", "\\")
    ledger_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    check("legacy Windows artifact paths remain portable", not run(base_text, ledger_path))
    artifact = ledger_path.parent / "evidence" / "E000001.txt"
    artifact.write_text("changed after capture", encoding="utf-8")
    records, ledger_errors = _load_evidence_ledger(str(ledger_path))
    check("validate carries evidence errors", validate(base_text, records)[0] == 1)
    check("validate_partial carries evidence errors", va.validate_partial(base_text, records)[0] == 1)
    command = [sys.executable, str(REPO_ROOT / "runtime" / "validate_adjudication.py"),
               str(ledger_path.parent / "adjudication-notes.md"), "--evidence-ledger", str(ledger_path)]
    for extra in ([], ["--phase", "adjudicate"], ["--next"]):
        result = subprocess.run(command + extra, capture_output=True, text=True, check=False)
        check(f"corrupt evidence blocks {extra or 'deliver'} readiness",
              "READY" not in result.stdout and (result.returncode != 0 or result.stdout.startswith("NEXT [evidence]:")))

    ledger_path = stage(tmp)
    source = ledger_path.parent.parent / "app.php"
    source.unlink()
    records, errors = _load_evidence_ledger(str(ledger_path))
    check("missing source is explicitly unverifiable", any("unverifiable" in error for error in errors))
    check("missing source cannot pass deliver", validate(base_text, records)[0] == 1)
    ledger_path = stage(tmp)
    with patch.object(va.shutil, "which", return_value=None):
        records, errors = _load_evidence_ledger(str(ledger_path))
    check("missing rg is explicitly unverifiable", any("unverifiable" in error and "rg" in error for error in errors))
    check("missing rg cannot pass deliver", validate(base_text, records)[0] == 1)
    with patch.object(va.subprocess, "run", side_effect=subprocess.TimeoutExpired("rg", 60)):
        records, errors = _load_evidence_ledger(str(ledger_path))
    check("timed-out searches cannot pass deliver", validate(base_text, records)[0] == 1 and any("unverifiable" in error for error in errors))

    # New read records bind the captured artifact to the source bytes.
    ledger_path = stage(tmp)
    source = ledger_path.parent.parent / "app.php"
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    rows[0]["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    ledger_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    check("matching source fingerprint is accepted", not run(base_text, ledger_path))
    source.write_bytes(source.read_bytes() + b"\n// changed\n")
    expect_rejected("changed source fingerprint is rejected", base_text, ledger_path, "source changed")
    source.unlink()
    expect_rejected("missing fingerprinted source is unverifiable", base_text, ledger_path, "source read is unverifiable")

    ledger_path = stage(tmp)
    records, _ = _load_evidence_ledger(str(ledger_path))
    schema = json.loads(va.SCHEMA_PATH.read_text())
    schema["unsupportedFutureRule"] = True
    bad_schema = tmp / "future-schema.json"
    bad_schema.write_text(json.dumps(schema))
    with patch.object(va, "SCHEMA_PATH", bad_schema):
        _, errors = validate(base_text, records)
    check("unsupported schema keywords fail explicitly", any("unsupported schema keyword" in error for error in errors))

if failures:
    print(f"\n{len(failures)} counter-example(s) FAILED: {failures}")
    raise SystemExit(1)
print("\nall counter-examples rejected as expected")
