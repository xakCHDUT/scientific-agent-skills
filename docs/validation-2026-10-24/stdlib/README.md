# Standard-library CI parity — 2026-10-24

Selected the same 24 suites as the original `skill-tests.yml`: `packages = []`, no interpreter override, and an existing suite. Every suite ran in a separate CPython 3.13.16 process with only pytest 9.1.1 and its dependencies. All 24 processes exited 0.

Result: **1269 passed, 22 skipped, 632 subtests passed; zero failures/errors.**

The 22 skips are existing opt-in live API checks (8 ARAX, 6 OLS, 8 LAPIS). They remained disabled. Test processes received a credential-free environment allowlist and a temporary `sitecustomize` that rejected Python socket connections. No real API key or private input was used.

| Suite | Passed | Skipped | Subtests |
|---|---:|---:|---:|
| analytical-method-validation | 140 | 0 | 15 |
| arbor | 53 | 0 | 21 |
| clinical-decision-support | 28 | 0 | 23 |
| clinical-reports | 28 | 0 | 20 |
| fictiv | 26 | 0 | 19 |
| generate-image | 87 | 0 | 8 |
| genomic-coordinates | 106 | 0 | 80 |
| hypothesis-generation | 31 | 0 | 14 |
| iso-standards-readiness | 25 | 0 | 37 |
| labarchive-integration | 47 | 0 | 69 |
| market-research-reports | 23 | 0 | 28 |
| ncats-arax | 66 | 8 | 74 |
| ontology-term-resolution | 108 | 6 | 9 |
| pacsomatic | 60 | 0 | 1 |
| paper-lookup | 91 | 0 | 65 |
| pathogen-variant-surveillance | 124 | 8 | 4 |
| peer-review | 30 | 0 | 7 |
| protocolsio-integration | 23 | 0 | 24 |
| pufferlib | 20 | 0 | 13 |
| scholar-evaluation | 38 | 0 | 0 |
| scientific-brainstorming | 19 | 0 | 27 |
| scientific-writing | 27 | 0 | 53 |
| treatment-plans | 29 | 0 | 0 |
| venue-templates | 40 | 0 | 21 |

Evidence: individual raw logs and JUnit XML, `environment.json`, and `summary.json` in this directory. JUnit counts include subtests in the `tests` total; the table keeps them separate. The scientific-writing console log contains progress only, but its finalized XML records all 27 testcases and 53 passing subtests, with zero errors/failures.

No source or test changes were needed for these suites. This is local Linux CI parity, not evidence that GitHub Actions ran, and not a full all-dependency suite sweep.
