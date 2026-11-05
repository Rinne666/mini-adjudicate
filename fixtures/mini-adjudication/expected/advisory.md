# Advisory — empty external-auth response rewrites the stored credential

> The report draft for claim C1 of `expected/adjudication-notes.md`.
> Validity `holds`, acceptability `accept`.
>
> **Draft only.** This Skill does not submit anything. Sending this
> advisory is the submitter's decision and requires explicit confirmation.

## Title

An empty external-authentication response must fail authentication
closed; it must never cause the stored credential to be derived from the
credential presented by an unauthenticated client.

## Affected component

- `fixtures/mini-adjudication/app.php` — `AuthService::login()`.
- The defect is at `app.php:116`; the branch that reaches it starts at
  `app.php:108`.
- The entry point is `AuthService::login()` at `app.php:99`, reached with
  a username and a password and nothing else.
- `default_auth.php:13-33` supplies the default adapter and wires it into
  this service; E000012 captures this source and its SHA-256.

## Attacker identity

An unauthenticated network client who knows only an existing username.

## Trust boundary crossed

From `L1 — anonymous` to `L3 — the permissions of the account whose
credential was rewritten`, which may be an administrator.

## Preconditions

- Attacker state: network access to the login endpoint, and the target
  username.
- System state: the fixture's default service composition in
  `default_auth.php:27-33`, with an existing account and no rate-limit
  environment override. The default limiter permits the request.
- The exact trigger is established by the implementation, not only the
  interface contract: `DefaultFixtureExternalAuth::authenticate()`
  unconditionally returns `''` at `default_auth.php:17`, and the default
  factory passes that adapter into `AuthService` at line 31.
- An ordinary unauthenticated login request therefore produces the empty
  response without a provider outage or operator change. A deployment
  using another, uninspected provider requires a separate assessment;
  unknown trigger control must remain `unknown` / `pending`.

## Same-version behaviour divergence

`AuthService::probe()` refuses the operation when the extension answers
empty (`app.php:134`), and `AdminService::login()` refuses the same
empty answer (`app.php:156`).

`AuthService::login()` writes the hash of the password the client
presented over the stored credential under that same condition
(`app.php:108`, `app.php:116`).

## Attack path

1. The client calls `AuthService::login($username, $password)` at
   `app.php:99`. No authentication gate precedes it; the method takes two
   strings and consults the limiter, whose default permits the request.
2. The extension is asked to authenticate (`app.php:106`) and answers
   with an empty body because the default factory installs the adapter
   whose return value is unconditional (`default_auth.php:17,31`).
3. The empty answer is matched at `app.php:108`. The branch reads it as
   "please set this password".
4. `Store::save()` is called with `password_hash($password, ...)` and
   the stored account's own `is_admin` flag (`app.php:116`), so the
   stored credential is replaced by the hash of what the client sent.
5. The method returns `true` (`app.php:117`). The client is
   authenticated against the hash that was just derived from its own
   input.

## Impact

Any password authenticates as the target account, and the session
carries that account's permissions — including the administrator flag,
which `save()` carries over from the existing record (`app.php:116`).

## Evidence

The deciding code:

> ```php
> if ($answer === '') {
>     $user = $this->store->find($username);
>     if ($user === null) {
>         return false;
>     }
>     $this->store->save($username, password_hash($password, PASSWORD_DEFAULT), $user['is_admin']);
>     return true;
> }
> ```
> — `app.php:108-118`

The negative control that would have disproved it: a check between the
empty test and the write that rejects the presented password. There is
none — the branch writes and returns unconditionally. The two sibling
paths that *do* refuse the same answer (`app.php:134`, `app.php:156`)
are what make this a divergence rather than a design choice.

The premise is independently supported by E000012: the source contains
both the unconditional empty return and the default constructor wiring.
E000008 and E000009 searched only `app.php`; they do not claim that the
repository lacks an extension implementation. E000013 captures SECURITY.md
for the scope, channel, and historical-classification assessment.

## Severity

`critical` — an unauthenticated client takes over any account whose
username it knows, and the account's own permissions, including
administrator, come with it.

**CVSS v3.1**: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N` → **9.1
(critical)**. The vector was cross-checked with `runtime/cvss31.py`.

`PR:N` because no credentials are needed to reach the login path;
`AC:L` because the default adapter returns empty deterministically for an
ordinary request; `S:U` because the scope is the same authority
realm; `C:H`/`I:H` because the client gains the account's readable and
writable data; `A:N` because nothing is made unavailable.

## Version and scope

- **Source reviewed**: `app.php` plus `default_auth.php` at the current
  fixture revision. This is a source-only teaching example; no PHP was
  executed and no live endpoint was tested.
- **Affected range**: every build that contains `AuthService::login()`
  with this branch.
- **Patched version**: none released.

## Why existing controls missed it

The invariant that an empty external-authentication answer must fail
closed was never enforced at the point where the login path interprets
that answer. It was enforced on the two sibling paths, which is why the
defect survived: the code that reads the empty answer as "please set
this password" is the only one that had to be changed, and nothing in
the type system or in the interface said that reading was allowed.

## Suggested remediation

Treat an empty extension answer as "no opinion" at the login path, the
same way the probe and the admin plane do. The smallest change is to
return `false` on the empty branch instead of writing the presented
password's hash over the stored credential.

Do not derive or replace a stored credential from an unauthenticated
login request. An alternative local-password fallback must verify the
presented password against the existing hash without modifying it. A
change that merely removes a comparison after the write does not repair
the credential overwrite.

## Notes for the submitter

Not part of the report body.

- Channel: `private-advisory-flow`, because every published advisory for
  this project came through it and the policy names no preference.
- Credit / attribution decision: **not decided here**.
- AI-assistance disclosure state: **not decided here**.
- **This advisory was not submitted by this Skill.** It is a draft.
  Submission requires the submitter's explicit confirmation.
