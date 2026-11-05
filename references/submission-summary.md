# Submission Summary

Read this at Deliver. The summary gives the submitter the reportable
claims, their proposed targets, and all blocking facts. It does not send
anything or certify that a target will accept a draft.

## Per-claim dimensions

Record these in each reportable claim's `submission` object:

| Dimension | Evidence to use |
|---|---|
| `severity` | Demonstrated harm and the scoring scheme used in the advisory |
| `core_business` | Product description, shipped component, or documented function; explain rather than infer importance from a directory name alone |
| `developer_awareness` | Comments, partial guards, linked issues, and inspected history |
| `trigger_configuration` | Literal default, enabling configuration, supported status, and who controls the trigger |
| `boundary_crossed` | From actor/capability → unauthorized actor/capability on the target's trust model |
| `targets` | Current policy fit with one primary and reasons for alternatives |

Core functionality can affect impact and program assessment, but is not
an automatic severity multiplier or guarantee of higher rewards. Record
installation or deployment counts only when supported; do not manufacture
a distribution argument for a registry.

For awareness, `aware` needs a specific cited record. `false` means no
awareness evidence was found within the stated search, not proof of the
developers' private knowledge. Use `unknown` when the relevant history is
unavailable. An existing TODO is not a fix; explain the remaining defect.

## Configuration consistency

`special_config_required` answers whether the trigger needs enabling
configuration beyond the stated default. `default_configuration` states
what that default actually is, with evidence. Keep supported optional
modes distinct from unsupported or weakened configurations.

The runtime rejects `special_config_required: true` together with
`premise_kind: attacker_only`. This is a coarse consistency rule, not a
universal platform rejection rule for non-default deployments. If the
facts do not fit the model neatly, state that limitation; do not hide the
configuration or silently redefine the default.

## Target provenance

Use [submission targets](submission-targets.md). Each proposed route needs
an applicable source record (`source_url`, `checked_at`, `program_scope`)
in the notes' Policy Sources section. Missing current rules make fit
provisional; they must not become an invented guarantee. The primary is
the proposed first intake, not an instruction to submit.

## Assemble from canonical state

Use [the summary template](../templates/submission-summary.md). The notes'
summary table is rendered from JSON; do not edit it independently. A
standalone summary must agree with that state.

- Include only `report` and `rewrite_then_report` claims in the reportable
  table, sorted by severity descending. Preserve the recorded order for
  ties; explain a different proposed sending sequence when useful.
- The `Order` column is a proposed delivery position. Follow the target's
  actual urgency/batching rules and the submitter's decisions; there is
  no requirement to wait for one response before drafting the next claim.
- Put `hardening_note` claims in a separate improvement section, explaining
  whether the limitation comes from policy or the acceptance heuristic.
- Below the reportable table, include missing technical facts from
  `needs_more_evidence`, acceptance `pending` and its `blocking_facts`,
  awareness that changes the framing, and untraced timeline fields.
- A reportable row's severity must agree with the advisory's stated rating.
  Explain the chosen scoring system when the target uses a different one.

If nothing is reportable, the written findings and blocked assessment are
still complete deliverables; do not fabricate a target list to fill an
empty table. Deliver all applicable artifacts together for review.
