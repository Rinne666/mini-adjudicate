# Written Finding — {slug}

> Use for `does_not_hold`, `needs_more_evidence`, `already_fixed`, or
> `holds` with acceptance `pending`. Retain only the sections relevant to
> this result. A blocked assessment is not a refutation of the defect.
> This artifact is not an advisory draft and has not been submitted.

## Claim as received

> {the original claim}

**Origin**: {scanner / colleague / advisory / supplied report / reading}.
**Source revision**: {commit / tag actually checked}.

## Decisions

- **Validity**: {does_not_hold / needs_more_evidence / already_fixed / holds}.
- **Acceptance**: {pending for holds with unknown premise; otherwise not applicable}.
- **Action**: {no_report / needs_evidence / already_fixed}.
- **Reason**: {what the captured evidence establishes and what remains unknown}.

## Assertions and evidence

| Assertion | Verdict | Evidence IDs and anchor | What it shows |
|---|---|---|---|

## If refuted: the decisive control or fact

Quote the guarding expression, unreachable condition, or other evidence.
Explain why it defeats this claim's particular path and identity; the
existence of an unrelated check is insufficient.

## If blocked: facts still needed

For `needs_more_evidence`, identify the missing defect/reachability/impact
fact. For `holds` plus `pending`, preserve the established conditional
defect and name what prevents classifying its premise. Copy the latter
facts into `acceptance.blocking_facts` in the canonical JSON.

| Missing fact | Why it changes the decision | Safe observation | Who can observe it |
|---|---|---|---|

State any incomplete boundary, divergence, or OSS-history checks. Do not
produce a vulnerability report for this claim until the blocking facts
are resolved and the assessment and gate have been rerun.

## If fixed: scope of the fix

- Fixing commit or guarding line, with captured evidence.
- Whether all affected paths were covered or a narrower residual remains.
- Whether the fix is released, and which release was verified.
- Publication status recorded separately: a published issue is not
  automatically fixed.

## Other refutation attempts

| Attempt | Result and supporting evidence |
|---|---|

## What would change the decision

Name the specific new observation that would change validity or
acceptance, and which part would change. Do not claim that resolving one
fact necessarily makes the issue reportable under every target policy.

## Submitter note

This is a written assessment for the submitter. No external report or
message has been sent by this skill.
