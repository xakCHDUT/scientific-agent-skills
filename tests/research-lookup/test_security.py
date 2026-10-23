"""Offline transport regressions: no real credentials, sockets, or model calls."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from requests.adapters import BaseAdapter

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "research-lookup" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_lookup import ResearchLookup  # noqa: E402


class MemoryAdapter(BaseAdapter):
    """Capture Requests' prepared requests without invoking a network adapter."""

    def __init__(self, status=200, location="https://untrusted.invalid/collect", reason=""):
        super().__init__()
        self.status = status
        self.location = location
        self.reason = reason
        self.seen = []

    def send(self, request, **kwargs):
        self.seen.append(request)
        response = requests.Response()
        response.status_code = self.status if len(self.seen) == 1 else 200
        response.reason = self.reason
        response.request = request
        response.url = request.url
        response._content = json.dumps({
            "choices": [{"message": {"content": "Synthetic public evidence."}}]
        }).encode()
        response._content_consumed = True
        if 300 <= response.status_code < 400:
            response.headers["Location"] = self.location
        return response

    def close(self):
        pass


class TransportSecurityTests(unittest.TestCase):
    KEYS = {"PARALLEL_API_KEY": "audit-parallel-dummy", "OPENROUTER_API_KEY": "audit-router-dummy"}

    def setUp(self):
        self.environment = patch.dict("os.environ", self.KEYS, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.path_lookup = patch("research_lookup.shutil.which", return_value=None)
        self.path_lookup.start()
        self.addCleanup(self.path_lookup.stop)

    def session(self, adapter):
        session = requests.Session()
        session.trust_env = False  # No proxies, .netrc, or environment credentials.
        session.adapters.clear()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        self.addCleanup(session.close)
        return session

    def test_authenticated_posts_refuse_every_3xx_without_forwarding(self):
        for backend in ("chat", "perplexity"):
            for status in (300, 301, 302, 303, 304, 305, 306, 307, 308, 399):
                for location in ("https://untrusted.invalid/collect", "http://untrusted.invalid/collect", "/moved"):
                    with self.subTest(backend=backend, status=status, location=location):
                        adapter = MemoryAdapter(status=status, location=location)
                        session = self.session(adapter)
                        lookup = ResearchLookup(force_backend=backend, manuscript_context={"question": "synthetic context"})
                        with patch("requests.post", side_effect=session.post):
                            result = lookup.lookup("synthetic query")
                        self.assertFalse(result["success"])
                        self.assertIn("redirect refused", result["error"])
                        self.assertEqual(len(adapter.seen), 1)
                        self.assertNotIn(location, result["error"])
                        for key in self.KEYS.values():
                            self.assertNotIn(key, result["error"])

    def test_success_keeps_expected_authentication_and_context(self):
        for backend, endpoint, header, value in (
            ("chat", "https://api.parallel.ai/v1beta/chat/completions", "x-api-key", self.KEYS["PARALLEL_API_KEY"]),
            ("perplexity", "https://openrouter.ai/api/v1/chat/completions", "Authorization", "Bearer " + self.KEYS["OPENROUTER_API_KEY"]),
        ):
            with self.subTest(backend=backend):
                adapter = MemoryAdapter()
                session = self.session(adapter)
                lookup = ResearchLookup(force_backend=backend, manuscript_context={"question": "synthetic context"})
                with patch("requests.post", side_effect=session.post):
                    result = lookup.lookup("synthetic query")
                self.assertTrue(result["success"])
                self.assertEqual(len(adapter.seen), 1)
                request = adapter.seen[0]
                self.assertEqual(request.url, endpoint)
                self.assertEqual(request.headers[header], value)
                body = request.body.decode()
                self.assertIn("synthetic query", body)
                self.assertIn("synthetic context", body)
                for key in self.KEYS.values():
                    self.assertNotIn(key, body)

    def test_error_reason_and_request_exception_echoes_are_redacted(self):
        echo = " / ".join(self.KEYS.values())
        for backend in ("chat", "perplexity"):
            with self.subTest(backend=backend):
                adapter = MemoryAdapter(status=400, reason=echo)
                session = self.session(adapter)
                lookup = ResearchLookup(force_backend=backend)
                with patch("requests.post", side_effect=session.post):
                    result = lookup.lookup("synthetic query")
                self.assertFalse(result["success"])
                self.assertIn("[redacted]", result["error"])
                for key in self.KEYS.values():
                    self.assertNotIn(key, result["error"])
                with patch("requests.post", side_effect=requests.ConnectionError(echo)):
                    result = lookup.lookup("synthetic query")
                self.assertIn("[redacted]", result["error"])
                for key in self.KEYS.values():
                    self.assertNotIn(key, result["error"])

    def test_cli_error_and_fallback_diagnostics_do_not_echo_keys(self):
        echo = " / ".join(self.KEYS.values())
        lookup = ResearchLookup(allow_perplexity_fallback=True)
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr=echo)
        with patch("research_lookup.subprocess.run", return_value=failed):
            with self.assertRaises(RuntimeError) as caught:
                lookup._run_parallel_cli(["search", "synthetic query", "--json"])
        self.assertIn("[redacted]", str(caught.exception))
        for key in self.KEYS.values():
            self.assertNotIn(key, str(caught.exception))
        stream = io.StringIO()
        with patch.object(lookup, "_parallel_search", side_effect=RuntimeError(echo)), \
             patch.object(lookup, "_perplexity_lookup", return_value={"success": True}), \
             patch("sys.stderr", stream):
            result = lookup.lookup("synthetic query")
        self.assertIn("[redacted]", result["fallback_reason"])
        for key in self.KEYS.values():
            self.assertNotIn(key, stream.getvalue())
            self.assertNotIn(key, result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
