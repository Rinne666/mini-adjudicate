# Report Writing

Read this when preparing a draft for a claim with validity `holds` and
acceptability `accept` or `accept_after_rewrite`. For refuted, fixed,
technically unresolved, or acceptance-pending claims, use
[the written finding template](../templates/refutation.md).

## State the failed invariant and observed impact

Use a title that names what the product fails to enforce. For example,
“An empty auth response rewrites the stored credential instead of failing
closed” is more precise than “Attacker can take over accounts.” Explain
the actual attacker capability in the impact section; do not erase it
from the report just to make the title sound narrow.

The title check is a limited pattern-based guard. It cannot prove that a
subject is an invariant or that the report establishes a vulnerability.
A rewrite improves the argument; it does not fix missing evidence or
change the target's trust model.

The draft should let a reviewer follow:

1. Affected component and exact revision or released version verified.
2. Attacker identity, credentials, and preconditions.
3. Entry point, control/data flow, and the failed invariant.
4. Boundary crossed and demonstrated consequence.
5. Reproduction or a complete static proof, with evidence references.
6. Suggested remediation and any residual uncertainty.

When a same-version divergence supports the claim, state both paths and
their conditions symmetrically. If absent, establish the intended boundary
from other evidence rather than implying that a comparison exists.

## Wording and uncertainty

State the configuration exactly, distinguishing a shipped default from a
supported optional mode and an unsupported weakening. Do not hide a
third-party dependency or imply the attacker controls it without proof.

Avoid attributing knowledge or intent without evidence. A TODO or old fix
can support developer awareness, but does not establish what every
maintainer currently knows. Cite the actual record when it matters.

Distinguish observed reproduction from static reasoning and proposed test
steps. Do not write “reproduced by me” on the submitter's behalf unless
they can substantiate it. Use only test data created for verification; if
real user data was confirmed reachable without retrieving contents, state
that limit directly.

Label untraced version ranges as unknown beyond the verified revision.
Describe the defective implementation, not “all versions” without evidence.
A patched version must identify a release that exists. For an unreleased
fix, name its commit and branch and leave the released-version field empty.

## Severity and CVSS

Use the scoring scheme the target requests. For CVSS v3.1, cross-check the
stated vector and score with the bundled implementation:

```text
python3 runtime/cvss31.py --selftest
python3 runtime/cvss31.py "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N"
```

Justify each non-obvious metric, such as why attack complexity is high or
availability is unaffected. The cross-check verifies arithmetic, not the
metric choices. This runtime does not calculate CVSS v4.0; use the target's
requested calculator when another version is required and identify it.

Keep the advisory, JSON submission severity, and summary consistent. The
reviewer decides final severity; do not imply the suggested score is an
accepted classification.

## Forms and later submission

This skill produces files. It does not fill or submit external forms.
Prepare text and metadata so the submitter can transfer them to the
current form. Read the live form instructions before any later authorized
submission; do not assume old field names, option values, or interactions
between manual severity and vector fields remain unchanged.

Record channel, credit/anonymity, disclosure timing, and applicable
assistance-disclosure rules in submitter notes outside the report body.
Use the verified source record for program-specific requirements. Prepare
all drafts now; sending order and any wait for replies belong to the
submitter's later plan.

## If feedback arrives later

Answer the actual question with verified facts. If the maintainer raises
a new precondition or policy interpretation, record the source, reassess
the affected claims, and rerun validation. A partial fix may leave a
separate residual claim, but establish that claim's reachability and
impact before classifying it. Feedback does not automatically turn every
residual defect into either hardening or a new vulnerability.

## Draft review

- Validity, acceptance, action, and evidence pass the explicit delivery gate.
- Preconditions, attacker identity, and boundary crossing are explicit.
- Each technical statement is supported; proposed steps are not described
  as observed results.
- Version, impact, vector, score, and summary agree.
- Target fit distinguishes current policy from a heuristic or inference.
- One primary channel is proposed and all applicable drafts are complete.
- The submitter can see remaining decisions and that nothing was submitted.
