# Independent security regression validation — 2026-10-24

Scope: the confidentiality fixes in PR #1, starting from
`9a007bb731bde2b22eb5f5b6156f2e2f51f9cbce`. This is verification of the
existing audit's specific fixes, not a second repository-wide security audit.
No production-code change was needed by this verification.

## Result

**PASS for the scoped fixes.** The dedicated run passed 31 pytest tests and
64 research subtests, with no skipped or failed tests. Seventeen tests are
new independent regressions. Counts describe test cases, not independently
audited features. See [command/output log](security-regression.log),
[machine-readable run record](security-regression.json), and the three
`security-*.xml` JUnit files beside this report.

| Boundary | Independent verification | Result |
|---|---|---|
| Parallel/OpenRouter research POST redirects | Existing real Requests in-memory transport tests rerun independently; explicit chat and Perplexity paths, ten 3xx codes, HTTPS/HTTP/relative locations; success authentication/context retained | Pass; only the intended request is sent |
| Four shipped schematic helpers | New isolated child process for each of `scientific-schematics`, `scientific-slides`, `literature-review`, `latex-posters`; real Requests redirect processing, no HTTP socket | All 2,400 combinations refused: four copies × two endpoints × every status 300–399 × three target forms |
| Schematic successful POSTs | Both image and review endpoints on every copy | Eight cases retain exact dummy Authorization and synthetic JSON payload; credentials absent from body |
| Schematic error diagnostics | Provider JSON error and transport-exception echoes, both endpoints on every copy | Sixteen cases redact the exact configured dummy key |
| Research diagnostics | HTTP reason, transport exception, external CLI error, explicit fallback reason/stderr | Configured dummy provider keys redacted |
| Imported citation batches | Actual CLI, classifier and extractor; forbidden last row in newline/JSON array/results/entries inputs, mixed with an explicit DOI | Entire batch stops before the first Requests call |
| Citation URL classification | Lookalike PubMed/arXiv/PMC/DOI hosts; credential-bearing known/generic hosts; malformed IPv6 URL | No unauthorized request; credential/invalid input rejected even with batch opt-in |
| Authorized signed webpages | Actual CLI-to-record pipeline, explicit URL and opted-in batch; mocked page → public DOI → Crossref metadata → BibTeX | Query retained for intended fetching; synthetic token, fragment and private path absent from diagnostics and returned public record |

The four schematic source copies also remain byte-identical, SHA-256:
`a349caba2eec391ed77822bb2bed3a4c5ee4434a317d6590a027d8049140757a`.
The separate full Linux suite run covers existing slide-generation, attachment,
review and successful-response tests; this dedicated count does not add those
again.

## Isolation and reproducibility

- Python 3.13, pytest 9.1.1 and Requests 2.34.2; exact commands are in the log.
- Test subprocesses receive an explicit environment allowlist without service
  credentials. Tests use hard-coded dummy values and synthetic records/images.
- A temporary `sitecustomize.py` rejects socket connect/connect_ex,
  create_connection and DNS lookups for the dedicated pytest processes.
- Schematic child probes additionally block their own sockets and DNS and mount
  in-memory adapters for both HTTP and HTTPS with `Session.trust_env = False`.
- Citation tests replace the Requests request boundary and also reject any
  unexpected underlying HTTP adapter send. No real provider call, private
  manuscript or unpublished research material is used.
- Each skill's tests run in its own interpreter; the four schematic copies are
  deliberately loaded in four separate children to avoid module-name collisions.

The new persistent tests are
`tests/citation-management/test_security_boundaries.py` and
`tests/scientific-schematics/test_security_transport.py`, with its executable
Python fixture under `tests/scientific-schematics/fixtures/transport_probe.py`.

## Residual risks and acceptance limits

This evidence supports merging these specific confidentiality fixes once the
other PR acceptance checks are satisfied. It does not certify live providers or
the whole skill collection. In particular:

- Explicit/opted-in webpage fetching and DOI resolution remain trusted-input
  interfaces; this batch authorization gate is not DNS-, IP- or redirect-safe
  SSRF protection. Hostile inputs still require network egress controls.
- Exact configured-key redaction does not cover encoded secrets, unknown CLI
  credentials, arbitrary sensitive prompt text or successful provider responses.
- Providers/proxies, ancestor `.env` discovery, inherited CLI environment and
  local rendering tools remain trust boundaries described in the original audit.
- Synthetic adapter success proves local authentication/payload behavior, not
  current live model availability or a billed end-to-end generation.
- Remote Actions and native-platform validation are separate acceptance items;
  an offline security pass cannot substitute for an unexecuted remote job.
