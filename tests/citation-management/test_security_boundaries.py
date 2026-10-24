"""Independent CLI-to-transport checks for the imported-webpage authorization gate.

Only synthetic bibliographic records and reserved .invalid URLs are used. These
tests keep the real CLI, classifier, metadata extraction and BibTeX rendering;
the Requests session request boundary is replaced, and sockets are forbidden.
"""

import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch

import pytest
import requests

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "citation-management"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import extract_metadata


@pytest.fixture(autouse=True)
def no_ambient_credentials_or_sockets():
    with patch.dict(os.environ, {}, clear=True), patch.object(
        socket.socket, "connect", side_effect=AssertionError("network forbidden")
    ), patch.object(
        requests.adapters.HTTPAdapter, "send",
        side_effect=AssertionError("unexpected HTTP transport"),
    ):
        yield


def invoke_cli(args):
    with patch.object(sys, "argv", ["extract_metadata.py", *args]), patch.object(
        extract_metadata.time, "sleep"
    ):
        try:
            extract_metadata.main()
        except SystemExit as error:
            return error.code
    return 0


@pytest.mark.parametrize("format_name", ["newline", "results", "entries", "array"])
def test_late_unapproved_url_blocks_explicit_and_imported_fetches(tmp_path, capsys, format_name):
    identifiers = ["10.1234/synthetic-public-doi", "https://publisher.invalid/paper?token=DUMMY_TOKEN"]
    if format_name == "newline":
        content = "\n".join(identifiers)
    elif format_name == "array":
        content = json.dumps(identifiers)
    else:
        content = json.dumps({format_name: [{"doi": identifiers[0]}, {"url": identifiers[1]}]})
    source = tmp_path / "references.txt"
    source.write_text(content, encoding="utf-8")

    with patch.object(requests.sessions.Session, "request") as request:
        code = invoke_cli(["--doi", "10.1234/explicit", "--input", str(source)])

    assert code == 2
    request.assert_not_called()
    diagnostics = capsys.readouterr().err
    assert "--allow-web-urls" in diagnostics
    assert "DUMMY_TOKEN" not in diagnostics
    assert "Processing" not in diagnostics


@pytest.mark.parametrize("url", [
    "https://pubmed.ncbi.nlm.nih.gov.attacker.invalid/12345/",
    "https://arxiv.org.attacker.invalid/abs/1706.03762",
    "https://pmc.ncbi.nlm.nih.gov.attacker.invalid/articles/PMC7611378/",
    "https://doi.org.attacker.invalid/article",
])
def test_lookalike_metadata_hosts_do_not_bypass_batch_gate(tmp_path, url):
    source = tmp_path / "references.txt"
    source.write_text(url, encoding="utf-8")
    with patch.object(requests.sessions.Session, "request") as request:
        assert invoke_cli(["--input", str(source)]) == 2
    request.assert_not_called()


@pytest.mark.parametrize("url", [
    "HTTPS://reader:DUMMY_PASSWORD@doi.org/10.1234/public",
    "https://reader:DUMMY_PASSWORD@publisher.invalid/paper",
    "https://[malformed-ipv6/paper?token=DUMMY_TOKEN",
])
def test_invalid_or_credential_url_prevents_entire_opted_in_batch(tmp_path, capsys, url):
    source = tmp_path / "references.txt"
    source.write_text("10.1234/public\n" + url, encoding="utf-8")
    with patch.object(requests.sessions.Session, "request") as request:
        assert invoke_cli(["--input", str(source), "--allow-web-urls"]) == 2
    request.assert_not_called()
    diagnostics = capsys.readouterr().err
    assert "invalid or credential-bearing URL" in diagnostics
    assert "DUMMY_PASSWORD" not in diagnostics
    assert "DUMMY_TOKEN" not in diagnostics


@pytest.mark.parametrize("input_mode", ["explicit", "batch"])
def test_authorized_signed_webpage_retains_fetch_query_and_completes_record(tmp_path, capsys, input_mode):
    url = "https://publisher.invalid/private/paper?access_token=DUMMY_TOKEN#DUMMY_FRAGMENT"
    webpage = requests.Response()
    webpage.status_code = 200
    webpage._content = b'<meta name="citation_doi" content="10.1234/synthetic-public-doi">'
    metadata = requests.Response()
    metadata.status_code = 200
    metadata._content = json.dumps({"message": {
        "type": "journal-article",
        "title": ["Synthetic public test title"],
        "author": [{"family": "Example", "given": "Alice"}],
        "published": {"date-parts": [[2026]]},
        "container-title": ["Synthetic Test Journal"],
    }}).encode("utf-8")
    if input_mode == "explicit":
        args = ["--url", url]
    else:
        source = tmp_path / "references.txt"
        source.write_text(url, encoding="utf-8")
        args = ["--input", str(source), "--allow-web-urls"]

    with patch.object(requests.sessions.Session, "request", side_effect=[webpage, metadata]) as request:
        assert invoke_cli([*args, "--format", "json"]) == 0

    assert request.call_count == 2
    assert request.call_args_list[0].args == ("GET", url)
    assert request.call_args_list[1].args == (
        "GET", "https://api.crossref.org/works/10.1234%2Fsynthetic-public-doi"
    )
    captured = capsys.readouterr()
    record = json.loads(captured.out)["entries"][0]
    assert record["doi"] == "10.1234/synthetic-public-doi"
    assert record["title"] == "Synthetic public test title"
    assert record["citation_key"]
    assert "@article{" in record["bibtex"]
    for sensitive in (url, "DUMMY_TOKEN", "DUMMY_FRAGMENT", "/private/paper"):
        assert sensitive not in captured.err
        assert sensitive not in captured.out
