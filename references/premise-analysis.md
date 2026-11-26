# Premise Analysis

Read this when classifying who creates the condition for a holding claim,
or interpreting its acceptance result. Keep this separate from technical
validity: a confirmed conditional defect may still lack the facts needed
to assess report readiness.

## Classify the condition

| `premise_kind` | Meaning and evidence needed |
|---|---|
| `attacker_only` | On the stated supported deployment, an **unprivileged or normal multi-tenant** attacker can create the trigger without another actor changing the system, and without holding an admin/code-execution role or internal infrastructure trust. Cite the entry point and attacker-controlled values. |
| `requires_privileged_or_trusted_channel` | Trigger requires an admin-equivalent / code-execution role (e.g., uploading custom executable code/bundles or `WRITE` on executable flow components with JVM/OS access) when no isolated principal or sandbox is breached, **or** requires a trusted infrastructure channel (cluster mTLS socket, loopback management port) secured by operator PKI/network deployment. |
| `requires_operator_decision` | A separate operator decision gates the attack. Cite the setting or deployment action and distinguish supported configuration from weakening a control. |
| `requires_ambient_state` | The trigger depends on concurrent activity, ordering, or system state the attacker has not been shown to control. Cite the dependency. |
| `requires_third_party_misconfiguration` | The trigger depends on extension/downstream behavior. Despite the legacy name, the behavior may be a documented response, not operator negligence. State the exact dependency. |
| `unknown` | Available evidence cannot establish who creates the trigger. Record what observation would settle it. |

Do not treat a seeded `WRITE` / code-upload role or a cluster-CA mTLS
certificate as `attacker_only` merely because a test harness can mint
them. Common traps that belong in `requires_privileged_or_trusted_channel`
(and resolve to `decline` / `hardening_note`):

- A custom code/bundle upload endpoint (`WRITE` / upload) writing files
  outside its storage directory: uploading custom code already implies
  code-execution privilege and trust over the uploaded artifact.
- An internal cluster socket protocol trusting a declared node ID without
  re-binding to the mTLS peer certificate: the cluster socket path itself
  is an operator-secured infrastructure boundary.
- A metadata/version write endpoint skipping validation when the caller
  already holds `WRITE` on that executable container and no isolated
  principal or restricted component is breached.

Do not infer attacker control merely because an input is allowed by an
interface. For example, a documented empty auth-hook response does not
by itself show that a requester can make a particular deployment return
it. Conversely, enabling a supported feature is not automatically a
security-weakening action. State the deployment and actor capabilities
precisely before choosing the closest category.

For a race, distinguish an attacker who controls both operations or can
hold a window open from one who relies on unrelated traffic. Retrying a
probabilistic condition can establish reproducibility, but it does not
make every environmental fact attacker-controlled.

A mixed premise retains every material dependency. Do not hide an
operator decision behind an attacker-controlled final request. If the
categories fit imperfectly, document the limitation in `rationale`; do
not rewrite the evidence to obtain a preferred matrix result.

## Unknown premise is a deliverable assessment

Use this combination when validity is `holds` but the premise is not yet
classifiable:

```json
{
  "premise_kind": "unknown",
  "acceptability": "pending",
  "rationale": "The defect is established; control over its trigger is not.",
  "blocking_facts": [
    "Observe whether the configured extension can return an empty answer for an attacker-selected username, using an isolated test account."
  ],
  "evidence_ids": ["E000001"]
}
```

This is an acceptance-object example, not a complete claim. Set the
claim's `action` to `needs_evidence`. Use real evidence IDs. Boundary and
divergence may be omitted while pending; if supplied, their values and
support must be valid. OSS verification may also remain unfinished for
this pending claim. Explain those limitations in the written finding.

The notes can pass delivery with pending acceptance and specific blocking
facts, but cannot turn that claim into an advisory draft. Do not change
technical validity to `does_not_hold` merely to finish the workflow.

## Acceptance matrix

The runtime preserves the following deterministic **heuristic**. Rows are
applied in order. It estimates report readiness from recorded inputs; it
does not predict an external reviewer's decision or replace program rules.

| Condition | Derived `acceptability` |
|---|---|
| Premise `unknown` | `pending` |
| Otherwise, boundary `declared_and_consistent` | `decline` |
| Otherwise, `privilege_ceiling.subsumed_by_existing_privilege` or `trusted_infrastructure_channel` is `true` | `decline` |
| Premise `requires_privileged_or_trusted_channel` | `decline` |
| Premise `attacker_only`, divergence `present`, clean `privilege_ceiling` | `accept` |
| Premise `attacker_only`, divergence `absent`, clean `privilege_ceiling` | `accept_after_rewrite` |
| Premise `requires_third_party_misconfiguration`, divergence `present`, clean `privilege_ceiling` | `accept_after_rewrite` |
| Other classified combinations | `decline` |

`accept_after_rewrite` is broader than fixing a consequence-style title.
Without a comparison path, the report must establish the violated
invariant directly. With a third-party dependency, it must explain the
product's responsibility and disclose the dependency. Preserve
`original_subject`, write the improved invariant in `subject`, and use
`rewrite_then_report`. If the original title already names an invariant,
record it honestly and improve the argument; do not invent a bad title.

The operator/ambient rows remain conservative even with a divergence.
A `decline` here means this heuristic recommends against a vulnerability
report, not that all programs reject such defects. Compare the outcome
with the target's actual scope and record any conflict or unsupported
assumption. Do not present the heuristic as a maintainer decision.

## Evidence and review

For each classified premise, identify the attacker's action, the separate
gating condition, and the line or observed fact connecting them. A
precondition that controls whether a path exists belongs in reachability;
a fact that controls whether harm occurs belongs in consequence. Their
uncertainty cannot be moved into premise analysis just to preserve `holds`.

The current runtime also rejects
`special_config_required: true` with `attacker_only`. Describe the literal
configuration and its supported status separately so reviewers can assess
what that coarse consistency rule does and does not express. A non-default
supported mode is not, by itself, evidence that a platform will reject a
report; consult its actual policy.

During final review, challenge both overstatements of attacker control
and unsupported dismissals. For pending claims, check that each blocking
fact is observable and that the proposed observation addresses the missing
fact without executing target code outside available isolation.
