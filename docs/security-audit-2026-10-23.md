# Targeted security audit: research, citations, and scientific slides

Audit date: 2026-10-23. Source baseline: [`a1043ef544e3a100c28e70a736b6cf32554d0677`](https://github.com/xakCHDUT/scientific-agent-skills/tree/a1043ef544e3a100c28e70a736b6cf32554d0677).

## Conclusion and scope

The reviewed source does not establish malicious credential harvesting, a past
leakage incident, or an automatic upload of unrelated manuscript files. It does
contain reproducible, conditional confidentiality defects and workflow risks.
The fixes accompanying this audit preserve declared authentication, literature
lookup, image generation, and explicitly authorized attachment use.

Deep review covered all **22 Python scripts (9,978 original source lines)** in
`citation-management`, `literature-review`, `research-lookup`, and
`scientific-slides`, their skill instructions and relevant references, and
existing tests. The identical schematic helper in `scientific-schematics` and
`latex-posters` was included and patched consistently. The repository tree,
scanner reports and scan/test workflows were also inspected. This is not a
complete code or dependency audit of all 177 skills. External `parallel-cli`,
`scholarly`, model providers, PDF/TeX renderers, transitive dependencies, remote
retention policies, and runtime installations remain separate trust boundaries.
Repository instructions were read as audit material, not used to execute an
academic workflow or upload user research data.

## What the existing scan actually says

The original JSON reports 177 scanned skills, 469 findings, 32 CRITICAL, 21 HIGH,
255 MEDIUM, 160 LOW, 1 INFO, and 159 skills classified safe. Its **92 per-skill
findings plus 377 cross-skill findings** sum to 469. Cross-skill findings comprise
1 HIGH, 233 MEDIUM and 143 LOW; the Markdown's per-skill table does not enumerate
them all. These are scanner findings, not 469 proven vulnerabilities.

Nine skills have two behavioral analyzer `FindingContract` errors involving
`UNKNOWN_BUNDLED_PYTHON_RULE`, including all four priority skills. No skill is
listed as skipped, but an empty skipped list does not mean every analyzer
completed successfully. The four priority skills account for 15 CRITICAL, one
MEDIUM and three LOW per-skill findings. Their environment-read/network patterns
require the actual source-to-sink review below. The historical triage's September
counts and older citation credential table do not describe this October source.
Neither the historical report nor its severity values was rewritten by this audit.

Evidence: [original JSON](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/docs/security-report.json),
[original Markdown](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/docs/security-report.md).

## Findings, ordered by practical risk

### A1 — Medium: redirects can forward credentials and research payloads

**Confirmed conditional vulnerability, not a demonstrated incident.**
`research_lookup.py` reads `PARALLEL_API_KEY` and places it in `x-api-key` before
POSTing to the fixed HTTPS Parallel Chat endpoint. Its OpenRouter path and the
slide/schematic helpers use standard Bearer Authorization. These calls originally
followed HTTP redirects by default.

In-memory Requests transport tests show that a cross-origin 307/308 forwards the
JSON body. The custom Parallel `x-api-key` header survives that hop; standard
Authorization is stripped on a cross-origin hop. Thus the OpenRouter observation
proves **payload** forwarding, not cross-origin Bearer-key forwarding. HTTPS to
HTTP redirection can also replay the body. A redirect from the configured service
or a trusted intercepting proxy is a necessary precondition; no ordinary query
directly chooses these fixed endpoint hosts, and no hostile live redirect was observed.

Original evidence: [research lookup, lines 746–845](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/research-lookup/scripts/research_lookup.py#L746),
[slide POST helper, lines 282–315](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/scientific-slides/scripts/generate_slide_image_ai.py#L282),
[shared schematic POST helper, lines 254–286](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/literature-review/scripts/generate_schematic_ai.py#L254).

**Minimal fix:** set `allow_redirects=False` and reject all 3xx before success or
JSON handling. `raise_for_status()` alone is insufficient for 3xx. Applied to both
research POST sites, the slide helper, and all four byte-identical schematic
copies. Successful requests retain their original authentication and payloads.
This does not protect against a malicious intended provider or a compromised CA/proxy.

### A2 — Medium: imported citation URLs implicitly trigger arbitrary webpage access

**Confirmed input-authorization weakness with conditional SSRF relevance.**
Search-result JSON or a newline input file can supply a generic `url`. The original
CLI passed it to `extract_record` and then `session.get`, including loopback/private
addresses. This matters when an agent consumes publisher-controlled results in a
network-privileged environment. Explicit `--url` is an intended URL-fetch feature;
it is not itself proof of unauthorized access. No internal service was contacted
in this audit, and no internal response exfiltration chain was demonstrated.

Original evidence: [URL classification](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/citation-management/scripts/extract_metadata.py#L50),
[web fetch, line 541](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/citation-management/scripts/extract_metadata.py#L541),
[batch URL fallback and CLI, lines 632–716](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/citation-management/scripts/extract_metadata.py#L632).

**Minimal fix:** check every imported identifier before the first fetch and require
`--allow-web-urls` for generic batch webpages. DOI/PMID/PMC/arXiv identifier URLs
continue working, and explicit `--url` remains supported. Credential-bearing input
URLs are rejected before a request. This is deliberately **not a complete SSRF
filter**: direct URL mode, opted-in batches, DOI resolution and redirects still
need trusted inputs or an egress policy blocking local/private networks. A naive
hostname blacklist would not establish DNS or redirect safety.

### A3 — Low: URL credentials and tokens can be printed in citation diagnostics

**Confirmed local confidentiality defect.** Generic URL classification, HTTP error,
no-DOI and exception messages printed the raw URL, including userinfo, signed query
parameters or private paths. A synthetic user/password/token URL was passed to a
mock GET and its password/token appeared in captured stderr in the baseline.
These are user-supplied URL secrets, not evidence of NCBI/OpenAlex key exfiltration.

Original evidence: [lines 541–564](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/citation-management/scripts/extract_metadata.py#L541),
[lines 578–607](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/citation-management/scripts/extract_metadata.py#L578).

**Minimal fix:** reject input URL userinfo and omit generic URL values and raw
request exceptions from diagnostics; retain HTTP status or exception type. Query
parameters remain available for explicitly requested legitimate webpages but are
not echoed in these diagnostics. This does not strip URL information from all
successful bibliographic outputs or prevent a trusted server returning sensitive text.

### A4 — Low: research error messages can echo configured API keys

**Confirmed conditional log/output exposure.** CLI stderr/error fields, HTTP error
reason/exception text and fallback diagnostics could reproduce a key if an upstream
dependency included it. Dummy-key error echoes reach baseline diagnostic sinks.
There is no evidence that the normal providers actually echo keys.

Original evidence: [CLI errors, lines 287–301](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/research-lookup/scripts/research_lookup.py#L287),
[error envelopes and fallback, lines 960–1008](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/research-lookup/scripts/research_lookup.py#L960).

**Minimal fix:** redact exact configured Parallel/OpenRouter key values from those
diagnostic paths. This does not sanitize arbitrary manuscript text, encoded secret
variants, successful service responses, or CLI-login credentials unknown to the
environment. Existing slide/schematic exact-key error redaction remains intact.

### A5 — Design risks: authorized uploads, credential discovery and local artifacts

- `--attach` reads the exact selected image paths and base64-encodes their bytes;
  generation sends them to OpenRouter and its model provider. The review step also
  reads and uploads the newly generated local image to a vision model. No unrelated
  file enumeration/upload was found. File extensions do not prove file content is
  suitable to share. Base64 is encoding, not encryption or anonymization.
- `--context-file` in research lookup reads the selected JSON object; **all nonempty
  fields**, including additional keys, enter the query context and can be sent to
  the selected backend. It is not an allowlisted PICO-only schema. This is an explicit
  input path, not automatic DOCX/PDF discovery.
- OpenRouter helpers search `.env` through the working directory's ancestors plus
  the script directory. They return the named key rather than uploading whole
  files, but can select another project's account. Parent `--api-key` can remain in
  shell history/process arguments even though wrappers omit keys from child argv.
- Slide/schematic wrappers already filter child environment variables. Research's
  external Parallel CLI inherits its parent's environment and receives context in
  argv. Treat that CLI and the process account as trusted, with a minimal environment.
- HTTP libraries may use configured proxies or `.netrc`. Prompts, reviews, result
  JSON and bibliographic artifacts can persist locally. Rendering tools process
  supplied Markdown/TeX/assets and are not security sandboxes.

Original evidence: [slide attachment read/encode](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/scientific-slides/scripts/generate_slide_image_ai.py#L347),
[schematic review upload](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/literature-review/scripts/generate_schematic_ai.py#L393),
[context transformation and CLI](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/research-lookup/scripts/research_lookup.py#L255),
[context file loading](https://github.com/xakCHDUT/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/research-lookup/scripts/research_lookup.py#L1028).

The patch makes upload destinations/secondary review transfer prominent in skill
instructions. Attachments and generated-image review remain functional. Broad
ancestor discovery and external CLI environment inheritance are documented residual
risks, not relabeled as fixed or as proven malicious behavior.

### A6 — Low: default vendor self-citation changes the user's bibliography

The citation skill previously directed adding its vendor's paper when it materially
contributed, with notice after insertion. This is a real workflow/academic-integrity
concern, not credential leakage. It now offers the citation and defers insertion to
the user's agreement or stated citation policy. The identical instruction was
updated in all six skills touched by this patch; the rest of the collection was
not globally audited or rewritten.

## Source-to-sink disposition of the priority skills

| Skill and scripts | Sensitive source / external sink | Assessment |
|---|---|---|
| citation: `search_pubmed.py`, `extract_metadata.py` | NCBI key/email to fixed NCBI E-utilities parameters; DOI to Crossref, arXiv/PMC identifiers to their declared metadata endpoints | Declared authentication/lookup. NCBI's API-key query parameter is expected; endpoint/proxy logs remain a boundary. No OpenRouter key read in current citation scripts. |
| citation: `search_openalex.py` | OpenAlex key to fixed API Bearer header; optional contact email to query | Declared authentication; dummy tests confirm key is not a query parameter or passed to generic webpages. |
| citation: `doi_to_bibtex.py`, `validate_citations.py` | Parsed DOI/identifiers to public metadata/DOI services | Expected validation/content negotiation; DOI redirects retained. No whole bibliography upload observed. |
| citation: `_common.py`, `format_bibtex.py` | Local bibliography parsing/formatting | No direct HTTP upload. |
| citation: `search_google_scholar.py` | Explicit search query to external `scholarly` dependency | Delegated API/proxy behavior outside bundled-code assurance. |
| literature: `generate_schematic.py`, `generate_schematic_ai.py` | Named OpenRouter key through filtered child env; prompt and generated-image bytes to image/vision APIs | Expected cross-script flow; A1 and A5 apply. Model image response accepts base64 data, not arbitrary download URLs. |
| literature: `verify_citations.py` | Reads selected manuscript locally, extracts DOI strings, sends DOI lookups and optional contact email | Does not send the whole manuscript. Its public generic HEAD helper remains a trusted-caller interface. |
| literature: `search_databases.py` | Selected JSON records to local deduplication/formatting | No HTTP or key read; its name alone is misleading evidence of network activity. |
| literature: `generate_pdf.py` | Selected Markdown/bibliography/template paths to Pandoc/XeLaTeX argv list | No shell-string interpolation or bundled HTTP upload; renderer trust remains necessary. |
| research: `research_lookup.py` | Named provider keys, queries and explicit context to fixed API requests or external CLI | A1/A4 fixed; inherited CLI environment/context transmission disclosed. OpenRouter fallback already requires explicit selection/opt-in. |
| research: `manuscript_packet.py` | Retrieved records to local Markdown/JSON/BibTeX | No HTTP, env reads or subprocess. Deep research reads its own temp report path, not an arbitrary response-selected file. |
| slides: `generate_slide_image.py`, `generate_schematic.py` | Named key to filtered child env; explicit prompts/paths to argv list | No shell interpolation and no key in child argv. Parent key flag remains optional and discouraged for sensitive use. |
| slides: `generate_slide_image_ai.py`, `generate_schematic_ai.py` | Key to OpenRouter auth; prompt, explicit attachments and generated image to provider APIs | A1 fixed; A5 documented. Returned remote image URLs are rejected by the base64-only decoder. |
| slides: `slides_to_pdf.py`, `pdf_to_images.py`, `validate_presentation.py` | Local presentation/PDF/TeX files to local conversion and validation | No direct model request. LaTeX validation already uses `-no-shell-escape`; this does not make untrusted rendering generally safe. |

The CRITICAL environment/cross-file findings identify these real sources and sinks,
but their malicious-exfiltration interpretation is unsupported for the declared
normal paths. The citation MEDIUM subprocess snippet uses an argument list;
its existence does not demonstrate shell injection. The attachment LOW finding
accurately identifies a data boundary and should not be dismissed as a false positive.

## Offline verification and limits

Regression tests use synthetic queries/images, `.invalid` destinations and dummy
keys. HTTP calls are intercepted by mocks or in-memory Requests adapters with
`trust_env=False`; no real service credentials or private research files were used.
Successful 200 auth/payload contracts, redirects, rejection before batch I/O,
diagnostic redaction and existing functionality are checked. The shared schematic
copies are kept byte-identical.

Tests live in `tests/research-lookup/test_security.py`,
`tests/citation-management/test_security.py`,
`tests/scientific-slides/test_current_contracts.py` and
`tests/_contract/schematic.py`. Run one skill per process, as required by the
repository's module-isolation contract. Local Windows results:

| Suite / check | Result | Limits |
|---|---|---|
| research-lookup | 26 passed | No skips; includes 60 redirect subcases and successful provider contracts |
| citation-management | 113 passed, 39 subtests passed | No skips; batch authorization and dummy credential routing covered |
| literature-review | 73 passed | No skips; includes its patched shared helper |
| scientific-slides | 149 passed, 116 subtests passed | No skips; includes actual Requests in-memory redirect transport |
| scientific-schematics | 32 passed, 71 subtests passed | One unchanged POSIX executable-bit check excluded on Windows |
| latex-posters | Complete attempt: 21 passed, 14 failed, 1 skipped | Failures involve Windows/WSL Bash access, missing POSIX tools or executable-bit semantics; `baposter.cls` is unavailable |
| latex-posters, precise platform exclusions | 21 passed, 44 subtests passed, 1 skipped, 14 deselected | This is not a passing full Linux suite; targeted schematic/review subset also passed 18 tests |
| Scoped structural contract | 54 checks passed across six changed skills | POSIX shell checks excluded; a scoped source snapshot cannot represent the full repository `_meta` suite |

The four priority suites total 361 passing tests; subtests and overlapping shared
helpers are not counted as additional independent audited features. Test runtimes
included Python 3.12/3.13 and Requests 2.32.x. Separate no-socket baseline probes
demonstrated redirect forwarding and URL logging; the revised paths refuse the
unapproved follow-up requests. No paid LLM scan was rerun locally, so the old
scanner totals are not post-fix measurements. A successful test run is not a
certification of all workflows, dependencies, or all 177 skills.

## Safe-use guidance

1. Use the audited revision plus these fixes; review the diff and pin deployments.
   Keep provider keys scoped, supplied at runtime, and out of shell arguments.
   Use a clean working directory/account without unrelated ancestor `.env` files,
   proxy credentials, `.netrc` entries or inherited service keys.
2. Use local bibliography formatting, JSON processing and rendering when content
   must stay local. Database queries still disclose queries/identifiers to their
   providers. Approve provider use before sending unpublished prompts, context
   JSON or attachments, including the automatic vision-review upload.
3. Prefer stable DOI/PMID/arXiv identifiers over arbitrary imported webpage URLs.
   Do not automatically add `--allow-web-urls` in response to a failed batch; review
   destinations. For adversarial URL inputs, enforce network egress controls across
   DNS resolution and redirects, including access to local/private services.
4. Treat returned citations, URLs and generated outputs as data, not instructions.
   Review references and local logs before sharing. Keep scanners as triage tools;
   recheck new source-to-sink flows when dependencies or skills change.
