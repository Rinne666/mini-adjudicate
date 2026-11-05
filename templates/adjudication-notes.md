# Adjudication Notes — {target}

> Prefer `python3 runtime/workspace.py init <notes.md> --target <name>`.
> This file illustrates the same layout. It is an incomplete scaffold;
> an empty claim list, missing evidence, or unfinished fields produce
> `NEXT` until completed. Do not present this template as a checked result.
>
> The JSON block is the only structured state. Edit it, then run
> `python3 runtime/workspace.py render <notes.md>`. Generated tables are
> replaced; analysis outside their markers is preserved. `render --check`
> detects drift. Legacy notes without these markers require deliberate
> migration rather than automatic replacement of their narrative.

## Analysis

Record the source revision and the reasoning a reviewer needs beyond the
structured facts: what was investigated, why a citation supports an
assertion, uncertainty, and what would change a verdict. Put the result of
a refutation attempt in its assertion's `refutation_attempted` field as
well; generated views draw from that record.

For a technically holding claim with unknown premise, use
`acceptance.premise_kind: unknown`, `acceptance.acceptability: pending`,
non-empty `acceptance.blocking_facts`, and `action: needs_evidence`.
Describe a safe way to observe each blocking fact. This is a completed
blocked assessment, not an advisory draft.

## Policy Sources

Record only sources actually consulted. Missing provenance remains
explicitly unknown; do not invent URLs, observation dates, or program fit.
Keep detailed provenance here rather than adding unsupported JSON fields.

| Claim / rule | source_url | checked_at | program_scope | Evidence / local path and revision | Status |
|---|---|---|---|---|---|

## Adjudication Table

Use `schemas/adjudication.schema.json` for fields and enums. `--claim` on
`init` can populate raw intake claims without inventing their conclusions.

<!-- adjudication:state:start -->
```json
{
  "target": {
    "name": "{target}",
    "kind": "open_source",
    "security_policy": {"source": "none", "ref": ""},
    "preferred_channel": ""
  },
  "claims": [],
  "coverage_paragraph_present": true,
  "work_queue": [],
  "channel": {"name": "", "reason": ""}
}
```
<!-- adjudication:state:end -->

<!-- adjudication:views:start -->

> Generated from the Adjudication Table JSON. Edit that JSON, then run render.

## Target and Source Ref

| Target | Kind | Policy source | Policy reference | Preferred channel |
| --- | --- | --- | --- | --- |
| {target} | open\_source | none | — | — |

## Claims Under Adjudication

No entries recorded.

## Claim Decomposition

No entries recorded.

## Assertion Ledger

No entries recorded.

## Acceptance Answers

No entries recorded.

## OSS Verification

No entries recorded.

## Verdict Table

No entries recorded.

## Submission Summary

No entries recorded.

## Work Queue

No entries recorded.

## Refutations Considered and Rejected

No entries recorded.

## Delivery Plan

| Channel | Reason | Alternative considered |
| --- | --- | --- |
| — | — | — |

<!-- adjudication:views:end -->

## Workflow commands

```text
python3 runtime/workspace.py render <notes.md>
python3 runtime/validate_adjudication.py <notes.md> --evidence-ledger <evidence.jsonl> --next
```

Before delivery, complete the work queue and final review, prepare every
applicable draft/written finding, and run `render --check` and the explicit
`--phase deliver` gate. Hook adapters are optional, require host setup,
and do not replace that explicit gate.
