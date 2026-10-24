"""Offline credential-routing and webpage-input boundary regressions."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'citation-management'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import extract_metadata
import search_openalex
import search_pubmed


class SecurityTests(unittest.TestCase):
    def setUp(self):
        # No ambient keys and no actual transport, including if a regression
        # causes a path the individual test did not expect.
        self.environment = patch.dict(os.environ, {
            'NCBI_API_KEY': 'DUMMY_NCBI_KEY', 'NCBI_EMAIL': 'ncbi@example.invalid',
            'OPENALEX_API_KEY': 'DUMMY_OPENALEX_KEY',
            'OPENALEX_EMAIL': 'openalex@example.invalid',
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.transport = patch.object(requests.sessions.Session, 'request',
                                      side_effect=AssertionError('Network is forbidden'))
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def run_main(self, args, record=None):
        output, diagnostics = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['extract_metadata.py'] + args), \
                patch.object(extract_metadata.MetadataExtractor, 'extract_record',
                             return_value=record) as fetch, \
                patch.object(extract_metadata.time, 'sleep'), \
                redirect_stdout(output), redirect_stderr(diagnostics):
            try:
                extract_metadata.main()
                code = 0
            except SystemExit as error:
                code = error.code
        return code, fetch, diagnostics.getvalue()

    def test_all_input_rows_checked_before_any_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'results.json'
            source.write_text(json.dumps({'results': [
                {'doi': '10.1234/valid'},
                {'url': 'http://127.0.0.1/internal?token=DUMMY_URL_TOKEN'},
            ]}), encoding='utf-8')
            code, fetch, diagnostics = self.run_main(['--input', str(source)])
        self.assertEqual(code, 2)
        fetch.assert_not_called()
        self.assertIn('--allow-web-urls', diagnostics)
        self.assertNotIn('DUMMY_URL_TOKEN', diagnostics)

    def test_batch_webpage_opt_in_preserves_supported_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'results.txt'
            source.write_text('https://example.invalid/paper\n', encoding='utf-8')
            code, fetch, _ = self.run_main(
                ['--input', str(source), '--allow-web-urls'], {'bibtex': '@misc{test}'})
        self.assertEqual(code, 0)
        fetch.assert_called_once_with('https://example.invalid/paper')

    def test_explicit_url_remains_supported(self):
        code, fetch, _ = self.run_main(['--url', 'https://example.invalid/paper'],
                                       {'bibtex': '@misc{test}'})
        self.assertEqual(code, 0)
        fetch.assert_called_once_with('https://example.invalid/paper')

    def test_known_identifier_urls_do_not_need_batch_opt_in(self):
        identifiers = [
            'https://doi.org/10.1234/paper',
            'https://pubmed.ncbi.nlm.nih.gov/12345/',
            'https://arxiv.org/abs/1706.03762v7',
            'https://pmc.ncbi.nlm.nih.gov/articles/PMC7611378/',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.txt'
            source.write_text('\n'.join(identifiers), encoding='utf-8')
            code, fetch, _ = self.run_main(['--input', str(source)], {'bibtex': '@misc{test}'})
        self.assertEqual(code, 0)
        self.assertEqual([call.args[0] for call in fetch.call_args_list], identifiers)

    def test_userinfo_rejected_even_with_batch_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.txt'
            source.write_text('https://user:DUMMY_PASSWORD@example.invalid/paper', encoding='utf-8')
            code, fetch, diagnostics = self.run_main(['--input', str(source), '--allow-web-urls'])
        self.assertEqual(code, 2)
        fetch.assert_not_called()
        self.assertNotIn('DUMMY_PASSWORD', diagnostics)

    def test_userinfo_rejected_before_http_and_diagnostics(self):
        extractor = extract_metadata.MetadataExtractor()
        for method in (extractor.extract, extractor.extract_record, extractor.extract_from_url):
            diagnostics = io.StringIO()
            with patch.object(extractor.session, 'get') as get, redirect_stderr(diagnostics):
                result = method('HTTPS://user:DUMMY_PASSWORD@example.invalid/paper?token=DUMMY_TOKEN')
            self.assertIsNone(result)
            get.assert_not_called()
            self.assertNotIn('DUMMY_PASSWORD', diagnostics.getvalue())
            self.assertNotIn('DUMMY_TOKEN', diagnostics.getvalue())

    def test_webpage_error_does_not_echo_url_or_exception(self):
        extractor = extract_metadata.MetadataExtractor()
        url = 'https://example.invalid/private/path?access_token=DUMMY_TOKEN#DUMMY_FRAGMENT'
        failures = [Mock(status_code=403), Mock(status_code=200, text='no DOI')]
        for reply in failures:
            diagnostics = io.StringIO()
            with patch.object(extractor.session, 'get', return_value=reply), redirect_stderr(diagnostics):
                self.assertIsNone(extractor.extract_record(url))
            self.assertNotIn(url, diagnostics.getvalue())
            self.assertNotIn('DUMMY_TOKEN', diagnostics.getvalue())
        diagnostics = io.StringIO()
        with patch.object(extractor.session, 'get', side_effect=requests.Timeout(url)), \
                redirect_stderr(diagnostics):
            self.assertIsNone(extractor.extract_record(url))
        self.assertNotIn('DUMMY_TOKEN', diagnostics.getvalue())
        self.assertIn('Timeout', diagnostics.getvalue())

    def test_ncbi_dummy_key_only_in_fixed_service_params_and_not_errors(self):
        searcher = search_pubmed.PubMedSearcher()
        diagnostics = io.StringIO()
        with patch.object(searcher.session, 'get', side_effect=requests.HTTPError('api_key=DUMMY_NCBI_KEY')) as get, \
                redirect_stderr(diagnostics):
            self.assertEqual(searcher.search('test'), [])
        self.assertEqual(get.call_args.args[0], 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi')
        self.assertEqual(get.call_args.kwargs['params']['api_key'], 'DUMMY_NCBI_KEY')
        self.assertNotIn('DUMMY_NCBI_KEY', diagnostics.getvalue())
        self.assertNotIn('DUMMY_OPENALEX_KEY', str(get.call_args))

    def test_openalex_dummy_key_only_in_authorization_header(self):
        searcher = search_openalex.OpenAlexSearcher()
        self.assertEqual(searcher.session.headers['Authorization'], 'Bearer DUMMY_OPENALEX_KEY')
        with patch.object(searcher.session, 'get', side_effect=requests.HTTPError('DUMMY_OPENALEX_KEY')) as get, \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError) as error:
                searcher.search('test')
        self.assertEqual(get.call_args.args[0], 'https://api.openalex.org/works')
        self.assertNotIn('DUMMY_OPENALEX_KEY', str(get.call_args.kwargs['params']))
        self.assertNotIn('DUMMY_OPENALEX_KEY', str(error.exception))

    def test_webpage_does_not_receive_other_service_keys(self):
        extractor = extract_metadata.MetadataExtractor()
        self.assertNotIn('Authorization', extractor.session.headers)
        with patch.object(extractor.session, 'get', return_value=Mock(status_code=404)) as get, \
                redirect_stderr(io.StringIO()):
            self.assertIsNone(extractor.extract_from_url('https://example.invalid/paper'))
        self.assertNotIn('DUMMY_NCBI_KEY', str(get.call_args))
        self.assertNotIn('DUMMY_OPENALEX_KEY', str(get.call_args))


if __name__ == '__main__':
    unittest.main()
