---
name: mini-adjudication
description: |
  Judge existing vulnerability findings after an audit: whether each claim
  holds, whether it is ready to report, and which disclosure channel fits.
  Produce evidence-backed verdicts, report drafts, and a submission summary.
  Use for "这个漏洞能不能报", "哪些能报", "报给谁", "is this reportable",
  or "validate this finding". Does not discover vulnerabilities or submit reports.
---

# mini-adjudication

Adjudicate existing claims with two separate decisions: **technical
validity** and **report readiness under the target's policy**. The runtime
checks evidence integrity and consistency; it cannot establish that a
claim is true or promise that a maintainer will accept it.

## Intake and boundaries

- Start with the user's existing findings and their source anchors. If no
  claims exist, explain that an audit is needed; do not start hunting.
- Record the target and exact source revision. A verdict applies to that
  revision, not automatically to every release or deployment.
- This skill produces drafts and checks. It does not submit, publish, or
  accept credit. External actions remain with the submitter.
- Read target code without executing it. If a material fact requires
  execution, use isolation the harness explicitly provides. Otherwise
  identify the missing fact and preserve the corresponding uncertainty.

## Workspace and driver

Use a separate adjudication workspace, not the installed skill directory.
Commands below run from the skill root with Python 3.10 or later. An
installed package also provides `mini-adjudication run <script.py> ...`,
which selects a compatible Python interpreter.

```text
python3 runtime/check_skill_loaded.py
python3 runtime/workspace.py init <notes.md> --target <name> --kind open_source --source-ref <commit-or-tag>
```

The freshness check compares files on disk with the packaged manifest. It
cannot inspect the model's context or prove alignment with Git HEAD. On
mismatch, inspect the installation and reload the intended files; do not
refresh hashes merely to hide a mismatch.

`init` creates a scaffold, not a completed adjudication. Add the claims
and evidence; the first driver run should report an unmet requirement.
The JSON block in the notes is the **only structured source of truth**.
Edit it, then regenerate its human-readable tables:

```text
python3 runtime/workspace.py render <notes.md>
python3 runtime/validate_adjudication.py <notes.md> --evidence-ledger <evidence.jsonl> --next
```

`render` updates generated regions and preserves handwritten analysis.
`render --check` detects generated-table drift without rewriting the file.
Do not independently maintain a second verdict in a Markdown table.
For format guidance see [the notes template](templates/adjudication-notes.md)
and [the schema](schemas/adjudication.schema.json).

The driver prints `NEXT [phase]: ...` or `READY`. Address the next unmet
requirement and re-run. The phases are `adjudicate`, `assess`, `deliver`;
earlier requirements must pass before later work is deliverable. Partial
notes are expected during work. `READY` can include a properly documented
blocked claim; it does not mean every claim is reportable.

Capture supporting reads and searches with `runtime/evidence_log.py`.
Evidence IDs refer to the ledger and hashed artifacts beside the notes.
Uncaptured tool output is exploratory until preserved as reviewable
support. Use bounded captures, not truncated evidence.

## 1. Adjudicate technical validity

Split each claim into independently testable assertions, then attempt to
refute each: an upstream guard, unreachable call path, protected caller,
unsupported execution path, or source change may defeat the claim. Record
the attempt and evidence even when it fails to refute.

A holding claim must establish **defect, reachability, and consequence**.
Do not relabel a missing reachability or impact fact as a precondition to
obtain `holds`. An uncertain environmental precondition can leave validity
intact while blocking the acceptance decision.

| Derived validity | Evidence state |
|---|---|
| `does_not_hold` | An assertion is refuted. |
| `already_fixed` | An assertion is fixed, with no refuted assertion. Cite the fix and its scope. |
| `needs_more_evidence` | A required technical fact remains unresolved. |
| `holds` | Defect, reachability, and consequence are confirmed; no assertion is refuted or fixed. |

For absence claims, capture two **distinct** zero-match searches and state
why their scope and patterns cover the proposed guard or alternative path.
Repeating a bad query does not prove absence. The validator replays
recorded zero-match searches; missing source or tooling makes that evidence
unverifiable and blocks delivery until resolved.

Read [claim decomposition](references/claim-decomposition.md) when splitting
an ambiguous claim and [validity assessment](references/validity-assessment.md)
when choosing a refutation or deciding what source cannot establish.

## 2. Assess report readiness

Only `holds` claims reach this stage. Record the target profile, policy
source (`stated`, `derived`, or `none`), and intended channel. The current
policy for this product and program is authoritative. Historical examples
and the built-in acceptance matrix are **heuristics**, not platform rules
or promises of acceptance. State any conflict or limitation explicitly;
do not change factual inputs merely to obtain a desired verdict.

Answer three questions and the Privilege-Ceiling Gate with evidence:

1. **Premise:** who creates the condition? Use `attacker_only`,
   `requires_privileged_or_trusted_channel`, `requires_operator_decision`,
   `requires_ambient_state`, `requires_third_party_misconfiguration`, or
   `unknown`.
2. **Boundary:** `declared_and_violated`, `declared_and_consistent`, or
   `not_declared`, based on the target's own trust model.
3. **Divergence:** `present` with both same-version paths cited, or
   `absent` with two distinct captured zero-match searches. Note that a
   divergence inside an already privileged role or trusted infrastructure
   channel indicates defense-in-depth inconsistency, not a CVE by itself.
4. **Privilege-Ceiling Gate (`acceptance.privilege_ceiling`):** record
   `caller_existing_ceiling`, `net_new_capability`,
   `subsumed_by_existing_privilege` (`true`/`false`), and
   `trusted_infrastructure_channel` (`true`/`false`). If the caller's
   starting role already grants code execution/admin power or the entry
   is an operator-secured internal channel and no isolated principal or
   sandbox is breached, the matrix derives `decline`.

The shared decision table is in
[premise analysis](references/premise-analysis.md#acceptance-matrix).
`accept_after_rewrite` signals that the argument or framing needs work
under that matrix; it is not determined solely by the title's wording.
Document the original subject and the revised invariant when rewriting.

If the premise is unknown, use `premise_kind: unknown`,
`acceptability: pending`, and `action: needs_evidence`. Populate
`acceptance.blocking_facts` with specific non-empty strings describing
what must be learned. Boundary/divergence and OSS verification may remain
unfilled while acceptance is pending; validate any fields already supplied.
Deliver the blocked assessment without a report;
do not turn uncertainty about acceptance into a false technical rejection.

For every open-source holding claim with a decided acceptance result,
complete `acceptance.oss_verification`: policy
fit, introducing commit, affected releases, fix/publication state,
similar issues, and maintainer practice. Use cited facts or explicit
`untraced — reason` entries; a prior classification is evidence to compare,
not proof that a different claim will receive the same answer.

Read only the references needed:

- [Acceptance policy](references/acceptance-policy.md): scope and authority.
- [Premise analysis](references/premise-analysis.md): preconditions and the matrix.
- [Commit timeline](references/commit-timeline.md): version and fix history.
- [Historical similarity](references/historical-similarity.md): prior cases and awareness.
- [Submission targets](references/submission-targets.md): choosing a channel;
  record `source_url`, `checked_at`, and `program_scope` for current rules.

## 3. Deliver the complete batch

Produce **all** applicable drafts and written findings in this run. Do not
wait for a response to one report before preparing another. Suggested
sending order is advice for the submitter, not a prerequisite for drafting.

| Validity / acceptance | Action and artifact |
|---|---|
| `holds` / `accept` | `report`: one advisory draft per claim. |
| `holds` / `accept_after_rewrite` | `rewrite_then_report`: a draft with the argument improved. |
| `holds` / `decline` | `hardening_note`: explain the heuristic/policy limitation and possible improvement. |
| `holds` / `pending` | `needs_evidence`: blocking facts and how to observe them; no report. |
| `does_not_hold` | `no_report`: the specific refutation. |
| `needs_more_evidence` | `needs_evidence`: missing technical facts and safe observation steps. |
| `already_fixed` | `already_fixed`: fix location, completeness, and release status. |

Use [advisory](templates/advisory.md) for reportable claims and
[written findings](templates/refutation.md) for refuted, fixed, or blocked
claims. If anything is reportable, produce the
[submission summary](templates/submission-summary.md): severity descending,
core business, developer awareness, trigger configuration, boundary
crossed, exactly one primary target, and reasons for alternatives.
Include all blocking facts below the reportable table, including pending
acceptance. `special_config_required: true` cannot coexist with
`attacker_only`; disclose documented configuration variants precisely.

For disclosure detail read [report writing](references/report-writing.md),
[summary guidance](references/submission-summary.md), and
[ordering and channels](references/ordering-and-channels.md). Cross-check
each stated CVSS v3.1 vector/score with `runtime/cvss31.py`; distinguish
verified versions from untraced ranges and unreleased fixes. Evidence of
impact must use data created for the test, not retrieved user contents.

Before delivery, close the work queue and complete `final_review`, including
an independent challenge to negative and pending conclusions. Check that
reports, summaries, and JSON agree, then run:

```text
python3 runtime/workspace.py render <notes.md>
python3 runtime/workspace.py render <notes.md> --check
python3 runtime/validate_adjudication.py <notes.md> --evidence-ledger <evidence.jsonl> --phase deliver
```

Deliver only after the gate passes. The schema, evidence checks, derived
verdicts, and table checks catch structural errors; a reviewer still owns
the truth of the claims and the fit to the target's actual policy.

## Optional harness integration

The package includes `runtime/session_start_check.py` and
`runtime/stop_gate.py`. **Installation does not register these hooks in a
host.** Configure them using that host's supported mechanism if wanted.
A configured Stop hook checks consistency during work and the full gate
when delivery is claimed, with a bounded escape to avoid endless host
retry loops. It is an advisory host safeguard, not an absolute block on
ending a turn. The explicit `--phase deliver` check remains authoritative.
Without hooks, run the commands above manually;
`doctor` checks the installation, not whether a host will invoke a hook.
