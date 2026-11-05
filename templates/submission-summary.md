# Submission Summary — {target}

> The 可申报总结: which drafts are reportable, their proposed routes,
> and what evidence or policy uncertainty remains. Produced at the Deliver stage for every claim whose action
> is `report` or `rewrite_then_report`. Claims whose validity is not
> `holds`, or whose acceptance is `pending`, do not appear in the
> reportable table. Blocked claims belong in Blocking facts below.

**Target**: `{name}` · kind `{open_source / closed_product /
web_service}` · policy `{stated / derived / none}` ·
adjudicated at `{commit / tag}`.

## Submittable

One row per reportable claim, **sorted by severity, descending**
(`critical` → `high` → `medium` → `low`; retain recorded order for
ties). The Order column keeps the proposed sending position. Actual
priority follows target instructions, urgency, and submitter decisions.
Prepare all drafts together; sending order does not block drafting.
Every cell cites or points at the adjudication.

| Order | Claim | Severity | Subject (invariant) | Core business | Developer aware | Special config | Boundary crossed | Primary target | Secondary / unsuitable |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C1 | `critical/high/medium/low` — one-line justification | | yes/no — evidence | aware/false/unknown — evidence | required? — default | from → to | `target` — reason | `target` — reason · `target` — reason |

## Hardening offers

Claims that hold but whose acceptability is `decline`: possible
improvements. Explain whether the limitation comes from the heuristic,
a verified policy rule, or both; do not imply a maintainer already rejected it.

| Claim | Why it will not be accepted as a report | The offer |
|---|---|---|

## Blocking facts

What stands between a blocked claim and submittability, stated so the
submitter can act on it:

- `needs_more_evidence` claims: the exact missing fact and the safe
  way to observe it.
- `holds` claims with `acceptability: pending`: the recorded
  `acceptance.blocking_facts`, observation steps, and incomplete checks.
- Any `developer_awareness: aware` finding and the re-framing it
  forces.
- Any timeline field that is `untraced`, and what a trace would change
  (affected range, already_fixed, publication status).

## Timeline (per submittable claim)

From `acceptance.oss_verification.commit_timeline` — cited facts or explicit
`untraced — reason`.

| Claim | Introduced | First release with it | Fix state | Published as |
|---|---|---|---|---|

## Decision points for the submitter

Not part of any report body. Recorded here because only the submitter
can decide them:

- Channel confirmation (one channel; the alternatives considered).
- Credit / anonymity decision.
- AI-assistance disclosure state under the specific verified program rule.
- Rule provenance: `source_url`, `checked_at`, and `program_scope`; name
  provisional target-fit conclusions where rules could not be checked.
- CNVD / CNNVD double-filing intent, if any — two submissions by
  design, never by accident.
- **Confirmation that nothing has been submitted by this Skill.**
  Submission and every externally visible action stay with the
  submitter.
