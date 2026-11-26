# Acceptance Policy

Read this when judging the policy fit of a technically holding claim.
The target's current instructions decide its scope and channel. The
skill's acceptance matrix is a heuristic; a matching label is not proof
of what the target will accept.

## Establish authority and provenance

Look for the current security policy, program brief, or reporting page.
Record the exact source, applicable product/version/program, and the date
you actually checked it. Use the handwritten Policy Sources section of
the notes for `source_url`, `checked_at`, and `program_scope`, plus captured
evidence references. A locally versioned policy can also carry its path
and commit; do not invent a web URL for it.

Mark `policy_source` as:

- `stated`: an applicable policy was found and read.
- `derived`: the interpretation comes from documentation/history rather
  than an explicit applicable policy; name the assumptions.
- `none`: no usable source was located; record where you looked.

A known policy conflict or missing applicability fact must be visible in
the assessment. Never turn absence of a policy into a made-up authority.

## Read the policy against this claim

Extract only what affects the decision:

- The trust model: actors, granted capabilities, and protected resources.
  Specifically check whether a role's legitimate capability already
  includes supplying custom code/plugins/scripts or accessing JVM/OS
  features (making that `WRITE`/upload role itself the security
  boundary), and whether peer protocols (cluster mTLS sockets, loopback
  management ports) are declared as operator-secured boundaries.
- Covered products, versions, deployments, assets, and issue classes.
- Explicit exclusions and any exceptions for supported configurations.
- Required evidence, reproduction conditions, and report format.
- Preferred channel, handling of duplicates, and disclosure conditions.

Distinguish **shipped default**, **officially supported configuration**,
and **unsupported or weakened configuration**. They are not synonyms. A
supported database or optional feature may be non-default and still in
scope. Follow the target's wording instead of assuming all non-default
states are excluded or relabeling them as literal defaults.

Record what the policy says about this claim's exact boundary. A product
statement that an action is deliberately allowed is relevant; a generic
claim such as "security matters" does not define a specific invariant.

## Use history as evidence, not a universal rule

Prior advisories, release notes, issues, and refusals provide comparisons.
For each relevant case, record its revision/date, premise, boundary,
consequence, and classification. Explain which parts match this claim and
which differ.

| Historical classification | What it supports |
|---|---|
| Security fix | The project treated that particular case as security-relevant. Compare the boundary and premise before extrapolating. |
| Bug fix | The prior case was published as functional maintenance; inspect whether the security consequence was the same or considered. |
| Hardening | The prior decision may indicate an intended trust boundary or insufficient demonstrated harm. Check the stated reason. |
| Wontfix/refusal | A decision in a particular context; it may clarify scope, but does not overrule a newer explicit policy automatically. |

A maintainer's old refusal does not always outweigh a current policy.
Public advisories do not reveal every private email intake. Do not infer
that a channel was never used or a future report must be accepted merely
from the visible history. Preserve disagreement and uncertainty rather
than turning an anecdote into an absolute rule.

## Choose the channel

Prefer the current explicit instruction. When it is silent, use available
reporting facilities and evidence of actual practice, marking the choice
as an inference. Record one primary channel with a reason and any planned
secondary registry steps. See [ordering and channels](ordering-and-channels.md).

Check relevant format, identity, encryption, attachment, and timing
requirements before drafting. Prepare the complete batch without sending
it or waiting for an external reply.

## Final policy check

A reviewer should be able to trace the stated policy fit to a source,
understand the configuration assumptions, and distinguish a target's
explicit rule from the skill's heuristic. If they cannot, revise the
assessment. The validator checks the recorded structure, not whether a
quoted policy really applies or whether a maintainer will agree.
