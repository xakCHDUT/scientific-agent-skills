# PR #1 independent acceptance — 2026-10-24

**Local acceptance: targeted security and Linux validation PASS.** The final hosted-CI decision and run URLs are recorded in [PR #1](https://github.com/xakCHDUT/scientific-agent-skills/pull/1), after this evidence commit has been tested. No additional production-code vulnerability was found during this verification. The original audit and its residual-risk statements remain valid; this is not a new full-repository security certification.

Original PR head: `9a007bb731bde2b22eb5f5b6156f2e2f51f9cbce`.
Base/main: `a1043ef544e3a100c28e70a736b6cf32554d0677`.
Remote commits `9d699a6` and `1226185` added a Linux/Windows regression workflow while this independent verification was in progress; they were fast-forwarded and preserved. The evidence in this directory covers the original security head plus the acceptance tests/platform changes in the containing commit. `linux-source-sha256.json` fingerprints the tested sources; `linux-summary.json` distinguishes the baseline commit from working-tree changes. A later workflow-only evidence-recording edit did not change tested code.

## Why no CI appeared

- An unfiltered repository-wide Actions query returned `total_count: 0`; the head's Checks API also returned zero. This is not merely the connector's PR-only filter or a mismatch between head and merge SHA.
- The repository is a public fork. Its public Actions page showed **No workflows found** and **0 workflow runs**, despite five tracked workflow YAML files.
- Both `pr-skill-scan.yml` and `skill-tests.yml` have matching `pull_request` path filters for this PR, and the non-draft PR is mergeable. Its head commit has no CI-skip directive. The base's historical `[skip ci]` commit does not by itself explain this new PR head.
- GitHub documents that workflows in forks do not run by default until Actions is enabled: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories>.
- **Leading diagnosis: fork workflows have not been enabled. This is an inference, not a directly read administrative setting.** The available GitHub connector does not expose the Actions settings/enable operation; its generic fetch rejects the workflow-list endpoint. The connected browser is signed out of GitHub, so the authenticated enable/settings page cannot yet be inspected. This session changed no Actions settings. During verification, new remote commits appeared and Actions started running. The subsequent run evidence supersedes the initial no-run state; the precise administrative activation action was not directly observed.
- On remote head `12261856f44b6841f587910c32a88611150d5e89`, [Research Security Regressions](https://github.com/xakCHDUT/scientific-agent-skills/actions/runs/40064850673) completed all 12 Ubuntu/Windows jobs successfully; Skill Tests and Skill Spec Validation also passed. PR Skill Scan returned success only because its missing-key report was published: the LLM scan did **not** run. The additional tests in this evidence commit require fresh hosted verification before merge.
- `main` is not branch-protected and has no required status checks in the returned branch metadata. Therefore GitHub's “mergeable” state is not evidence of a passing CI gate. No branch protection was weakened.

## Minimal changes

1. Preserve the existing contract and 24 standard-library suite jobs. Extend the concurrently added `research-security-regressions.yml` six-skill Ubuntu/Windows matrix: the existing selector excludes all six because their dependency lists are nonempty.
2. Record exact interpreter/package versions, commands, JUnit and logs as 30-day Actions artifacts. The matrix injects no provider secrets and runs pytest with `--disable-socket`.
3. Skip only genuinely POSIX Bash/executable-bit/TeX-preflight tests on native Windows, while preserving their Linux execution and keeping static asset checks portable. This does not claim that Bash helpers support native Windows; use a POSIX environment for those helpers.
4. Make paid LLM scans explicitly opt-in with repository variable `ENABLE_LLM_SECURITY_SCAN=true`, for both PR and weekly workflows. Scanner code, thresholds and reports are preserved. Without opt-in, the job explicitly reports **not run**, which is not a passing security assessment. This prevents default credential use while performing the requested no-real-keys validation.
5. Add 17 independent offline tests for citation batch boundaries and actual Requests transport across all four schematic copies. No production script behavior was altered in this follow-up.

## Verified results

All skill suites ran in separate CPython 3.13.16 processes with isolated dependencies. Tests received synthetic inputs and dummy credentials; no unpublished material or real provider API key was used. Local test processes had Python socket guards; the final six-skill run additionally used pytest-socket. Package installation was separate from test execution.

| Check | Passed tests | Passed subtests | Skips |
|---|---:|---:|---:|
| research-lookup | 26 | 71 | 0 |
| citation-management | 126 | 39 | 0 |
| literature-review | 73 | 53 | 0 |
| scientific-slides | 149 | 116 | 0 |
| scientific-schematics | 37 | 71 | 0 |
| latex-posters | 36 | 44 | 1 |
| Repository structural/coverage guard | 18 | 4,224 | 0 |
| Existing CI's 24 standard-library suites | 1,269 | 632 | 22 |

No failures or errors. The six changed suites total **447 passing tests**. The full table totals **1,734 passing tests and 5,250 passing subtests**; this does not include additional overlapping targeted reruns. JUnit's `tests` field includes subtests, so do not sum it as independent test functions.

- The 14 previously failing Windows/POSIX latex checks pass unchanged on Linux. Real available TeX/Poppler integrations executed. One optional compilation check remains skipped because `baposter.cls` is unavailable.
- The 22 standard-library skips are existing opt-in live API tests: ARAX 8, OLS 6 and LAPIS 8. They were deliberately not enabled.
- `skills-ref validate` passed for all **177 skills**, using upstream validator commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`.
- Dedicated security rerun: 31 tests and 64 subtests passed, no skips. It overlaps the suites above. The new schematic probe covers all HTTP 300–399 statuses, two endpoints and three redirect-target forms across four shipped helpers: **2,400 single-send refusals**, eight successful authentication/body checks and 16 diagnostic redaction checks.
- All six workflow YAML files parse; Python workflow bodies compile. Actionlint validation and the exact-tooling smoke results are recorded in the workflow evidence files. The preceding remote matrix passed, but the final follow-up revision must be checked independently; do not reuse earlier-head green checks as final evidence.

## Remaining risks and merge conditions

- Direct or explicitly opted-in citation URL access, DOI redirects and DNS resolution remain trusted-input interfaces, not a complete SSRF defense. Untrusted inputs in network-privileged environments still require egress restrictions.
- Intended providers, proxies/CA trust, external CLI behavior, ancestor `.env` discovery and local renderers/artifacts retain the boundaries described in the original audit. This run did not audit all 177 skills or all dependencies.
- No live provider integration or paid LLM security scan ran. Passing offline checks cannot certify provider behavior or data-retention policy.
- Native Windows compatibility of the portable Python paths is validated by the hosted Windows matrix; require fresh results after the added regressions. Bash-only behavior is covered on Linux and not declared native-Windows compatible.

Before merge, push the integrated follow-up to generate a PR synchronize event, verify the resulting runs actually refer to the intended head/merge revision, inspect all Ubuntu/Windows and existing contract/suite results and skips, and archive the run URLs/artifacts. The repository now runs Actions, so another activation request is unnecessary. Do not opt into paid scans for this no-real-keys acceptance. Fix any real failures without relaxing functional assertions. Refresh PR/base/head state, then merge with the validated head SHA only if no blocker remains. User authorization to merge is already present; another merge-permission question is unnecessary.

## Evidence map

- `linux-summary.json`, `linux-source-sha256.json`, `*-linux.log`, `*-linux.xml`, `*-environment.json`: final Linux results and environments.
- `linux-baseline-summary.json`: earlier baseline/preparation record, retained to avoid hiding setup retries.
- `security-regression.md`, `.json`, `.log`, and `security-*.xml`: independent security probes.
- `stdlib/`: all 24 existing-CI suite logs, XML, environment and summary.
- `skills-ref.log`, `skills-ref-summary.json`: all-skill specification validation.
- Workflow validation evidence and the original [security audit](../security-audit-2026-10-23.md).
