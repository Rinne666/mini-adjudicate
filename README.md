# mini-adjudication

Evidence-backed triage for findings that already exist. This agent skill
separates **whether a vulnerability claim holds** from **whether it is
ready to report**, then produces advisory drafts, written findings, and a
submission summary. It does not discover vulnerabilities or submit reports.

The three-stage workflow is **Adjudicate → Assess → Deliver**. Python
validates the structured record, evidence artifacts, and derived verdicts;
Node provides installation and a portable runtime launcher. Neither can
prove a maintainer will accept a report. The target's current policy takes
precedence over the skill's acceptance heuristics.

## Install and check

```text
# From this checkout:
node bin/cli.js install

# From a package you built:
npm pack
npx ./mini-adjudication-<version>.tgz install

# After publication to npm:
npx mini-adjudication@latest install
```

The CLI requires Node >= 18. Runtime tools require Python >= 3.10; source
search capture and replay also require `rg` (ripgrep). The launcher detects
a compatible Python interpreter instead of assuming `python` is the right
one.

Scopes: `--user` (default: `~/.agents/skills/` + `~/.zcode/commands/`),
`--zcode` (`~/.zcode/skills/`), `--claude` (`~/.claude/skills/` +
`~/.claude/commands/`), and `--all`. `--link` uses a checkout instead of a
copy and is not intended for an npm cache. Install receipts track owned
files; `uninstall` uses that record.

```text
node bin/cli.js doctor
node bin/cli.js doctor --full
```

`doctor` checks installation integrity, interpreter availability, and the
trigger commands (`/adjudicate` and `/cnvd-pack`). `--full` additionally runs
the regression suite. The CLI installs both skills (`mini-adjudication` and
`cnvd-packager`) and their trigger commands (`/adjudicate` and `/cnvd-pack`);
**it does not register host SessionStart or Stop hooks**. The optional adapters
are described in [SKILL.md](SKILL.md#optional-harness-integration). Without
host integration, run the validation commands explicitly.

## Start an adjudication

Load [SKILL.md](SKILL.md) after an audit has produced candidate findings.
Keep generated files in a separate workspace. From the skill checkout:

```text
node bin/cli.js run check_skill_loaded.py
node bin/cli.js run workspace.py init /path/to/adjudication-notes.md --target example --kind open_source --source-ref <commit> --claim "The existing finding to verify"
```

The installed executable accepts the same `run` arguments:

```text
mini-adjudication run workspace.py init /path/to/adjudication-notes.md --target example
```

For direct invocation, replace `node bin/cli.js run <script.py>` with
`python3 runtime/<script.py>` using Python >= 3.10. `--claim` may be
repeated; it records the supplied claim without inventing assertions or
verdicts. A fresh scaffold is intentionally incomplete and will yield
`NEXT`, not `READY`.

1. **Adjudicate:** decompose each claim, attempt to refute it, and capture
   supporting reads/searches with `runtime/evidence_log.py`. A holding
   claim needs confirmed defect, reachability, and consequence assertions.
2. **Assess:** for holding claims, record the premise, declared boundary,
   and same-version divergence. Check the target's policy. Open-source
   claims additionally record commit/release history, similar cases, and
   maintainer practice. Unknown premise means pending acceptance, not an
   invented rejection or an assumed exploitable configuration.
3. **Deliver:** prepare all applicable drafts and written findings in the
   batch. Suggested sending order never requires waiting for an external
   reply before preparing another draft.

The notes contain one canonical JSON state. Generated Markdown tables are
views of it; handwritten analysis and policy sources remain outside the
generated region. After editing state:

```text
node bin/cli.js run workspace.py render /path/to/adjudication-notes.md
node bin/cli.js run validate_adjudication.py /path/to/adjudication-notes.md --evidence-ledger /path/to/evidence.jsonl --next
```

Address each `NEXT [phase]` requirement and repeat. Before delivery:

```text
node bin/cli.js run workspace.py render /path/to/adjudication-notes.md --check
node bin/cli.js run validate_adjudication.py /path/to/adjudication-notes.md --evidence-ledger /path/to/evidence.jsonl --phase deliver
```

`render --check` reports drift without modifying the notes. Legacy notes
without generated-region markers are not overwritten automatically; migrate
their state and handwritten analysis into an `init` scaffold first.

## Decisions and artifacts

| Technical validity | Acceptance | Result |
|---|---|---|
| `holds` | `accept` | Advisory draft |
| `holds` | `accept_after_rewrite` | Draft with argument/framing improved |
| `holds` | `decline` | Hardening note with the policy/heuristic limitation |
| `holds` | `pending` | Blocking facts; no report |
| `does_not_hold` | Not applicable | Refutation |
| `needs_more_evidence` | Not applicable | Missing technical facts and observation steps |
| `already_fixed` | Not applicable | Fix location, completeness, and release status |

The acceptance matrix is documented in
[premise analysis](references/premise-analysis.md#acceptance-matrix).
`accept_after_rewrite` follows the premise/boundary/divergence combination;
it is not a title-style detector. If the premise cannot be classified,
record `premise_kind: unknown`, `acceptability: pending`,
`action: needs_evidence`, and non-empty `acceptance.blocking_facts`.
A complete assessment containing such a blocked claim can pass delivery;
that claim still cannot have a report action.

When claims are reportable, the submission summary lists severity, core
business, developer awareness, trigger configuration, boundary crossed,
and exactly one primary target per claim. Target categories are
`vendor_advisory`, `cve_cna`, `cnvd`, `src_platform`, `bounty_platform`, and
`hardening_channel`. Their current program rules need recorded
`source_url`, `checked_at`, and `program_scope`; the bundled reference is
routing guidance, not a live policy database.

## What validation guarantees

- Schema constraints and phase requirements are checked; both verdicts
  must agree with their recorded inputs and the action must match.
- Cited evidence IDs resolve to untruncated artifacts with matching hashes;
  confirmed/refuted assertions cite captured source reads.
- Absence evidence uses two distinct searches. Recorded zero-match
  searches are replayed; missing source or search tooling blocks delivery
  instead of silently treating absence as verified.
- Open-source holding claims carry the required verification record;
  reportable claims carry submission details and a single primary target.
- The work queue is closed and final review is recorded before delivery.

These are consistency guarantees. The runtime cannot prove that a search
pattern covers the right scope, a citation supports its interpretation,
a source read demonstrates real-world impact, or an external reviewer
will accept the result. A passing gate is not a vulnerability certificate.

## Repository map

| Path | Purpose |
|---|---|
| `SKILL.md` | Concise agent workflow and reference routing |
| `references/` | Claim reasoning, policy/history checks, reporting guidance |
| `templates/` | Notes layout, advisory, written finding, summary |
| `schemas/adjudication.schema.json` | Structured state contract |
| `runtime/workspace.py` | Scaffold notes and render canonical state |
| `runtime/validate_adjudication.py` | Phase gates and evidence consistency |
| `runtime/evidence_log.py` | Read/search captures and hash-bearing ledger |
| `runtime/cvss31.py` | Independent CVSS v3.1 score cross-check |
| `bin/cli.js`, `cli/` | Installer, launcher, and trigger commands (`/adjudicate`, `/cnvd-pack`) |
| `skills/cnvd-packager/` | Companion post-adjudication CNVD packaging skill (`cnvd-packager`) |
| `fixtures/`, `runtime/test_*.py` | Regression inputs and counterexamples |

## CNVD Packaging Pipeline (`/cnvd-pack` / `cnvd-packager`)

Separate from `/adjudicate` (which adjudicates source-grounded validity and
reportability without touching live deployments), the bundled
[cnvd-packager](skills/cnvd-packager/SKILL.md) skill and `/cnvd-pack` command
handle post-adjudication CNVD delivery:

1. **Filter & Align:** ingest `mini-adjudication` (`accept` / `accept_after_rewrite`) or `security-audit` (`confirmed`) outputs and align target URLs + low-privilege test accounts.
2. **Capture Evidence:** execute live verification and save key screenshots (`screenshots/`) covering the exploit execution and verified impact.
3. **Render Word + Video:** render a unified 5-section CNVD `.docx` report (overview, source location, illustrated reproduction, impact, remediation) and produce `复现视频.mp4` meeting the declarative Chinese-voiceover video acceptance gate.
4. **Bundle:** assemble `{产品名}_{漏洞类型}_{简短标识}/` containing the `.docx`, `复现视频.mp4`, optional `poc/`, and `screenshots/`.

Run `npm test` for regression checks. After intentional changes to tracked
skill files, refresh the manifest using
`node bin/cli.js run check_skill_loaded.py --refresh`, then rerun tests.
