# Delivery Order and Channels

Read this when a batch has several claims or the target offers multiple
intake channels. This guidance affects the proposed submission plan, not
whether the skill finishes preparing the batch.

## Draft the whole batch

Produce one advisory draft per reportable claim and the appropriate
written finding for every other claim. Prepare all of them in the same
adjudication run. Do not wait for a maintainer response before writing a
second draft: this skill does not send the first one.

The summary table is sorted by severity descending. Its `Order` column
records a suggested sending order; the two orders need not be identical.
Follow any explicit target instructions for batching and urgency. Consider
active impact and severity alongside evidence completeness, policy fit,
and how quickly a reviewer can verify the claim. There is no universal
rule that low-severity issues must be sent before critical ones.

A clear `attacker_only` premise and a cited same-version divergence can
make a report easier to review. `accept_after_rewrite` means its argument
needs to address a limitation in the heuristic matrix; finish that work
before marking its draft ready. `pending` acceptance and negative validity
verdicts do not enter the report order. Hardening notes are separate offers.

## Choose a primary channel

Use the target's current published instructions. Record why the selected
channel fits and what alternatives were considered. Exactly one primary
per claim prevents accidental duplicate intake. An advisory history can
help interpret an unspecified preference, but it does not override an
explicit current channel instruction or prove that email was never used.

Private advisory systems, security email, and program portals have
different identity and formatting requirements. Check the relevant
requirements, such as subject format, encryption, attachments, and
requested disclosure timing, before declaring a draft ready.

The target may permit or require coordinated submissions to a vendor and
a registry. Represent those as planned secondary steps with their
conditions, not simultaneous duplicate intake by default. Record any
CNVD/CNNVD filing intent separately; this skill does not send either.

## Submitter decisions

Keep these outside the report body:

- Primary channel, permitted follow-up channels, and any batching advice.
- Credit or anonymity preference and whether the channel supports it.
- Disclosure timing and any verified program-specific assistance rules.
- Confirmation that this skill has prepared drafts without submitting them.

## Reassess after feedback

If the submitter later supplies a closure or requested changes, compare
the feedback with this claim's actual premise and boundary. Record the
source and what it changes. A previous refusal is evidence of a decision
in a particular context, not a universal rule for unrelated claims.

Revise the affected draft or verdict when the evidence warrants it, and
rerun the gate. A residual defect or a different same-version divergence
must be established independently; changing the title alone does not
create a new vulnerability.
