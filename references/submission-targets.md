# Submission Targets

Read this when a holding claim is being routed to a disclosure channel or
registry. These categories help organize the decision; this file is not a
live database of eligibility, rewards, certificate requirements, or program
windows. The current rules for the specific product and program prevail.

## Provenance before platform-specific claims

For every platform rule used in an assessment, record the following in
the notes' handwritten **Policy Sources** section, outside generated views:

| Field | What to record |
|---|---|
| `source_url` | The exact authoritative page actually consulted; use `null` if unavailable and explain why. |
| `checked_at` | The actual observation date/time, preferably ISO 8601; never a guessed refresh date. |
| `program_scope` | The product, assets, program, region, or rule edition to which the source applies. |
| `rule` | The particular requirement used in this decision. |
| `evidence` | Captured excerpt/artifact or versioned local-policy reference. |
| `status` | Verified for this assessment, superseded, or unverified. |

Do not add these fields to `submission.targets` unless the schema supports
them; keep the provenance record in analysis and cite it in the target's
reason. A local `SECURITY.md` can use its path and commit as evidence when
there is no authoritative URL.

This reference ships **no pre-verified platform rules**. Its initial
provenance state is explicit:

| Target family | `source_url` | `checked_at` | `program_scope` | Status |
|---|---|---|---|---|
| Maintainer advisory | `null` | `null` | Target product; must be established | Unverified |
| CVE/CNA | `null` | `null` | Assigning authority and product; must be established | Unverified |
| CNVD | `null` | `null` | Applicable submission lane; must be established | Unverified |
| SRC | `null` | `null` | Named vendor, assets, and activity rules; must be established | Unverified |
| Bounty program | `null` | `null` | Named program and asset scope; must be established | Unverified |

Replace missing metadata only after reading the source. If rules cannot
be checked, say that target fit is provisional. Do not describe a reward,
CVE assignment, originality credit, or certificate as guaranteed.

## Target vocabulary

| Target | Intended route | What must be checked |
|---|---|---|
| `vendor_advisory` | Maintainer/vendor security intake | Product scope, supported versions, current preferred channel, required evidence |
| `cve_cna` | An assigning authority covering the product | Current scope, assignment procedure, references/version requirements, coordination with the vendor |
| `cnvd` | The named national vulnerability database | Applicable lane, current eligibility/evidence rules, publication restrictions, originality/certificate terms if relevant |
| `src_platform` | A vendor's Security Response Center | Ownership and listed assets, issue classes, activity windows, disclosure conditions |
| `bounty_platform` | A named bounty program | Program-specific assets, exclusions, reproduction requirements, severity policy, assistance/disclosure rules |
| `hardening_channel` | Improvement proposal rather than a vulnerability report | Project's preferred patch/issue flow and whether public detail is appropriate |

Each reportable claim has exactly one `primary` target. Other listed
targets are `secondary` or `unsuitable`, with specific reasons. A secondary
entry is a possible later step, not authorization to submit a duplicate.
The user decides the actual disclosure plan.

## Maintainer and CNA coordination

For an open-source component, start by identifying the maintainer's
published security instructions and any applicable CNA. A private
advisory facility may connect those processes, but do not assume all
hosting providers assign identifiers automatically, that publication and
assignment happen at the same time, or that a reporter can use the same
route for every product.

Record affected revisions and any verified released range. If the
introducing change is untraced, name that uncertainty; do not replace it
with an invented release boundary. Separate identifier reservation,
publication, and severity decisions in the proposed timeline.

## CNVD and other registries

Distinguish a defect in a distributed product/component from a finding in
one deployed instance. Use the applicable current rules to determine the
submission lane and evidence required. Do not infer product distribution
or impact from a single test instance.

CNVD and CNNVD are separate destinations. If the user wants coordinated
filings, record that intent and verify each destination's conditions;
this skill does not submit either. Avoid treating simultaneous filing as
a universally required or universally forbidden action.

## SRC and bounty programs

Read the named program's rules, not another vendor's example. Verify the
asset scope, report requirements, exclusions, handling of existing public
issues, and any special activity period. A shared component used by a
vendor does not automatically make every deployment an in-scope asset.

Suggest severity using the taxonomy the program actually uses. Do not map
an issue name such as XSS, RCE, or CSRF to a fixed priority without the
relevant context and program rule. If AI-assistance disclosure matters,
record the exact applicable instruction; do not assume every program has
the same requirement.

Use only test data created for verification and preserve the evidence
needed for the stated boundary crossing. A draft should include affected
asset/component, preconditions, replayable steps or a complete static
proof, observed impact, and suggested remediation as the target requests.

## Routing procedure

1. Identify the target product/assets and their owner or maintainer.
2. Read the current applicable policy and record provenance above.
3. Compare the claim's premise, boundary, versions, and evidence to it.
4. Choose one primary route and explain the status of alternatives.
5. Mark unresolved eligibility as provisional and state what to check.
6. Produce the complete draft batch and summary for the submitter.

A `needs_more_evidence` validity verdict or `pending` acceptance does not
have a report to route yet. A technical refutation is an internal written
finding. A heuristic `decline` supports a hardening offer; explain any
conflict with the target's explicit policy instead of asserting that the
maintainer has already rejected a report they have never received.
