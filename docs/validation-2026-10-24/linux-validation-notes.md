# Linux acceptance evidence — 2026-10-24

The original PR suites and the acceptance additions were run in separate pytest processes per skill on Linux x86_64, CPython 3.13.16. Each skill received its declared dependencies from `tests/skill-requirements.toml` in a separate `uv --no-project` environment; package versions are recorded in the environment JSON files.

The final run used `pytest>=9.1.1`, `pytest-socket --disable-socket`, and a temporary inherited `sitecustomize` guard that refused socket connections. Test environments were rebuilt from an explicit allowlist, excluding real API keys, access tokens and proxy credentials. Dependency preparation ran separately before the offline tests. Test inputs were repository fixtures, generated synthetic artifacts and dummy credentials; HTTP provider operations were mocked or transported through in-memory Requests adapters.

| Suite | Tests passed | Subtests passed | Skipped |
| --- | ---: | ---: | ---: |
| `_meta` (repository-wide) | 18 | 4,224 | 0 |
| `research-lookup` | 26 | 71 | 0 |
| `citation-management` | 126 | 39 | 0 |
| `literature-review` | 73 | 53 | 0 |
| `scientific-slides` | 149 | 116 | 0 |
| `scientific-schematics` | 37 | 71 | 0 |
| `latex-posters` | 36 | 44 | 1 |
| **Total** | **465** | **4,618** | **1** |

All seven pytest processes exited 0. JUnit counts include subtests; the table separates them to match pytest's console convention. Some text logs omit the trailing console summary, so each log includes a recorder footer with the exit code and complete JUnit aggregate counts.

The sole skip is the optional real `baposter` template compilation: `baposter.cls` is not installed. Real `beamerposter` and `tikzposter` compilation/preflight tests passed using installed TeX Live and Poppler. All 14 POSIX-dependent checks that previously failed on Windows passed unchanged on Linux before platform-specific test markers were added. This does not establish native Windows execution; that needs the workflow's Windows runner result.

The citation suite emitted a third-party `scholarly` SyntaxWarning about an invalid regex escape. A transient socket-block warning appeared in the schematics suite; an additional complete run with `--disable-socket -W error` passed 37 tests and 71 subtests, with no warning (see `schematics-warning-check.log`). No real provider request was allowed.

`linux-baseline-summary.json` records the original PR suite results before acceptance additions. `linux-summary.json`, `*-linux.xml`, and `*-linux.log` record the final supplemented run. `linux-source-sha256.json` records source hashes at test time. The only later source change was workflow metadata recording actual interpreter/dependency versions; skill scripts and test files remained unchanged, as recorded in `linux-summary.json`. `reproduce_linux.py` reconstructs the same per-skill process/environment method; exact resolved dependency versions remain in the individual environment JSON files.
