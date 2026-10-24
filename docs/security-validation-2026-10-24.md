# PR #1 independent validation — 2026-10-24

## Acceptance decision

The security patch is eligible for merge within its documented scope. No blocking
functional or security regression was found. All 12 Linux/Windows regression
jobs, the repository contract, 24 standard-library skill suites and skill-spec
validation passed on `12261856f44b6841f587910c32a88611150d5e89`.
The final PR head must be checked again before merging this evidence-only update.
This is not a certification of all skills, dependencies or hostile-input safety.

The original audit and source patch remain intact:
[2026-10-23 audit](security-audit-2026-10-23.md), original patch
`9a007bb731bde2b22eb5f5b6156f2e2f51f9cbce`, baseline
`a1043ef544e3a100c28e70a736b6cf32554d0677`.

## Actions investigation and minimal change

- The original head returned no workflow runs and no legacy commit statuses.
  The public Actions page also showed zero runs. Empty legacy statuses alone
  are not proof of missing checks; the workflow-run query was checked separately.
- Existing `pull_request` triggers and `skills/**` path filters match this PR.
  No branch filter, draft restriction or merge conflict explains the absence.
- A real branch update through the connected GitHub app immediately triggered
  all three existing PR workflows and the new regression workflow. Subsequent
  updates triggered them again, without changing repository Actions settings.
  Therefore current triggering works; this is not an ongoing Actions-disable or
  malformed-trigger issue. The exact historical cause of the initial absent
  event is unproven: available records do not expose that event's delivery or
  suppression history. Do not present a token-suppression hypothesis as fact.
- A separate, confirmed coverage gap existed: `skill-tests.yml` selects only
  `packages = []` suites. All six affected skills declare packages and were
  excluded from that job. Added `research-security-regressions.yml` with six
  skills on Ubuntu and Windows, one isolated dependency environment per skill,
  read-only contents permission, no persisted checkout credential, no provider
  secrets, socket-blocked pytest and JUnit artifacts.
- The first new run's tests passed but its setup-uv cleanup failed because the
  sanitized child environment omitted uv's configured cache directory. The
  follow-up preserves only `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` in addition
  to the existing environment allowlist. The second run passed all 12 jobs.
  No production script, test assertion or existing required workflow was weakened.

## Results

Counts below are test cases; repeated shared-helper checks and subtests are not
additional independent security features.

| Suite | Local Linux | Actions Ubuntu | Actions Windows |
|---|---:|---:|---:|
| research-lookup | 26 passed | 26 passed | 26 passed |
| citation-management | 113 passed | 113 passed | 113 passed |
| literature-review | 73 passed | 73 passed | 73 passed |
| scientific-slides | 149 passed | 149 passed | 149 passed |
| scientific-schematics | 33 passed | 33 passed | 32 passed; 1 POSIX check deselected |
| latex-posters | 35 passed; 1 skipped | 33 passed; 3 skipped | 20 passed; 16 platform checks deselected |
| Total affected suites | 429 passed; 1 skipped | 427 passed; 3 skipped | 413 passed; 17 deselected |

Local Linux also passed the repository-wide contract: **18 tests and 4,224
subtests**. The affected suites passed **394 subtests** on each platform.
Actions' existing standard-library runner reports **24 suites passed, 0 failed**;
individual optional-dependency skips in those unrelated suites remain visible in
its logs. Skill Spec Validation also passed.

Windows exclusions are explicit: `ReviewScriptTests`, `TemplateCompilationTests`
and `test_the_bundled_example_is_executable_shell`. They concern POSIX execute
bits, Bash/Poppler fixtures and shell-based TeX preflight, not Python security
behavior. Those shell assertions remain enabled and passing on Linux. This does
not claim native-Windows support for Bash tooling. Local Linux compiled both
beamerposter and tikzposter templates, including real-asset paths. The optional
`baposter.cls` was absent; hosted Ubuntu had no `pdflatex`, so all three hosted
template compilation tests skipped. The template assets were not changed by PR #1.

## Security and functional evidence

- Authenticated research calls reject 300–399 responses, including cross-origin,
  downgrade and relative locations, without replaying prompts/context or keys.
- Slide/image and shared schematic POST regressions cover redirects and preserve
  successful authentication, generation, explicit attachments and vision review.
- Imported generic webpage batches require opt-in and validate every row before
  extraction. Explicit URLs and known DOI/PMID/PMC/arXiv paths remain functional.
- Userinfo URL rejection, diagnostic redaction and provider-specific credential
  routing pass. Four schematic helper copies remain identical under `_meta`.
- Independent negative controls copied current tests into temporary trees and
  restored only the corresponding production script from the original baseline.
  Research redirect checks then failed all 60 subcases; the citation whole-batch
  authorization test also failed. Both pass on the patched source. These controls
  used mocked extraction/in-memory transports, never live internal endpoints.
- All model credentials and manuscript/image inputs used in tests were dummy or
  synthetic. No unpublished research was uploaded. Tests ran with an allowlisted
  environment and `pytest-socket --disable-socket`; package installation still
  accesses package registries. This pytest control is not an OS sandbox for all
  subprocesses. Local test runtime was CPython 3.13.16; hosted logs record their
  resolved Python/runtime versions.

## Remaining risks and non-blocking gaps

1. Direct/opted-in webpage fetches, DOI resolution and redirects still require
   trusted input or external DNS/redirect-aware egress controls. This patch is
   not a complete SSRF filter and must not be deployed as one.
2. The intended provider still receives authorized query/context/attachment data,
   including generated-image vision review. Provider retention, `.env` discovery,
   proxy/`.netrc` behavior and external CLI environment inheritance remain trust
   boundaries documented in the original audit.
3. The PR scanner workflow ran, but explicitly skipped the model scan because
   `SKILL_SCANNER_LLM_API_KEY` was unset. Its successful job status means the skip
   path completed, not that a new scan found no issues. No real model API key was
   used and no paid model scan was performed. Historical scanner findings and
   Codex/Copilot review limitations remain unchanged.
4. Optional baposter compilation, live-provider integration, all scientific
   dependency suites and exhaustive hostile-input security were not validated.
   These are outside the corrected transfer paths; no such coverage is claimed.
5. Non-blocking warnings include scholarly's invalid escape sequence, prevented
   socket creation in synthetic error paths, and existing third-party Action
   deprecation warnings. They are not silently counted as security certification.

## Reproducible and retained evidence

- [Cross-platform regression run](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064850673)
  — 12 successful jobs with separate JUnit artifacts.
- [Repository contract and 24 standard-library suites](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064850636).
- [Skill specification validation](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064850671).
- [Scanner skip evidence](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064850667).
- [Initial cache-cleanup failure](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064768845)
  is retained rather than hidden.
- [Permanent evidence archive](security-validation-evidence-2026-10-24.zip)
  contains local stdout, per-suite JUnit XML, full negative-control output and
  hashes, plus remote job/log summaries. Remote artifacts have retention limits;
  the committed archive preserves the local evidence independently.

Reproduce each affected suite with its packages from
`tests/skill-requirements.toml`, adding `pytest` and `pytest-socket`:

```bash
uv run --no-project --python 3.13 --with pytest --with pytest-socket \
  --with requests python -m pytest tests/research-lookup -q -ra --disable-socket
```

The workflow contains the complete executable command construction for all six
suites and the documented Windows selection. Execute one skill per process.
Run `_meta` separately with pytest/jsonschema installed. For a meaningful Linux
poster compilation check, install the documented TeX and Poppler dependencies;
do not interpret a dependency skip as a successful compilation.
