# CI and cross-platform follow-up — 2026-10-24

## Findings

- At the original PR head `9a007bb731bde2b22eb5f5b6156f2e2f51f9cbce`, the PR scan, skill tests, and spec-validation workflows all select the changed `skills/**` paths. The PR is same-repository, non-draft, and its commit message contains no CI-skip directive. These facts do not explain an absent run.
- The root validation session independently observed zero repository-wide Actions runs and a public Actions page saying “No workflows found”. The repository is a fork. Fork workflow activation / repository Actions settings remain the leading explanation, but the public page alone cannot establish the authenticated administrative setting. A successful test run must not be inferred from an empty API result.
- The old `skill-tests.yml` suite selector only runs entries with `packages = []`. All six skills changed by PR #1 have nonempty dependency lists; the existing suite job therefore does **not** run them, even when Actions is enabled.
- The old same-repository PR scanner and weekly scanner inject a real LLM credential when configured. They need a separate explicit opt-in to avoid invoking a paid model during credential-free validation.
- While this follow-up was in progress, the PR advanced to `12261856f44b6841f587910c32a88611150d5e89`, which adds a working dedicated `research-security-regressions.yml` with the six-skill Linux/Windows matrix and a sanitized environment. The final changes extend that workflow rather than adding duplicate jobs to `skill-tests.yml`. Remote execution evidence is recorded by the root acceptance report.

## Changes

1. Retained the existing repository contract and standard-library suite jobs unchanged. Extended the existing dedicated six-skill `research-security-regressions.yml` matrix on `ubuntu-latest` and `windows-latest`, using the dependency manifest and Python 3.13. Each suite has its own process/environment, per `AGENTS.md`.
2. The regression jobs use no secrets, disable credential persistence during checkout, and run pytest with `pytest-socket --disable-socket`. Their existing environment allowlist is preserved, including Windows startup paths, uv cache/interpreter locations, and UTF-8 mode; provider credentials are excluded. Tests supply synthetic keys and mocked/in-memory transports. This is a pytest socket guard, not an operating-system firewall: CLI child processes still rely on their no-network test paths and credential-free environment.
3. Added JUnit XML, raw stdout/stderr, exact command, commit identity, platform, actual test interpreter, and resolved dependency versions as 30-day artifacts, including on failure.
4. Linux poster jobs install TeX and Poppler, so the Bash preflight and available real-template checks run. `baposter.cls` remains an explicitly reported optional dependency gap if it is absent.
5. Native Windows skips only POSIX-specific behavior: 12 Bash/permission poster tests, 3 template/preflight tests that invoke the Bash helper, and 1 schematic executable/Bash test. Platform decorators replace the earlier workflow's `-k` deselection, so skip reasons appear in logs/JUnit. Portable content checks remain active, including a new poster-script presence/shebang check. The complete POSIX tests still run on Linux. This does not claim the Bash helper is a native Windows program.
6. Both paid scanner workflows now require `vars.ENABLE_LLM_SECURITY_SCAN == 'true'` before scheduling the secret-bearing job. The opposite condition produces a visible “not run” explanation, explicitly **not** a passing security assessment. Scanner functions, thresholds, and reports remain intact for opted-in runs.

## Verification and limits

- All six workflow YAML files parse; the regression Python step compiles.
- Official `actionlint` 1.7.12, downloaded from its release and checked against the published SHA-256 list, accepts all six workflows. `shellcheck` and `pyflakes` were unavailable and were not claimed as run. See `ci-static-validation.txt`.
- A direct invocation matching the new matrix ran `research-lookup` with pytest >=9.1.1 and `--disable-socket`: 26 passed, 71 subtests passed. The same invocation for `scientific-schematics`: 37 passed, 71 subtests passed. One whole-suite run emitted a blocked-socket warning; the named test rerun alone with `-W error` passed. Full guarded Linux evidence is recorded separately by the Linux validation run.
- YAML/actionlint and local Linux execution alone do not establish that GitHub scheduled a job or that native Windows passed. Use the acceptance report's remote run/job evidence for those conclusions and check the associated SHA; an earlier green run does not validate later changes. Do not treat platform skips, absent runs, or a skipped paid scan as successful validation of those surfaces.

Reference documentation used to check workflow syntax and context availability:

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
