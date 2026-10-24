"""No-network Requests probe used by test_security_transport.py, not a live API client."""

import importlib.util
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

import requests
from requests.adapters import BaseAdapter


KEY = "DUMMY_SCHEMATIC_VERIFICATION_KEY"
BODY = {"model": "synthetic-model", "prompt": "synthetic public diagram",
        "input_references": [{"image_url": {"url": "data:image/png;base64,c3ludGhldGlj"}}]}


class MemoryTransport(BaseAdapter):
    def __init__(self, status, location=None, content=b'{"synthetic":true}'):
        self.status = status
        self.location = location
        self.content = content
        self.seen = []

    def send(self, request, **kwargs):
        self.seen.append(request)
        response = requests.Response()
        response.status_code = self.status
        response.url = request.url
        response.request = request
        response._content = self.content
        response._content_consumed = True
        if self.location is not None:
            response.headers["Location"] = self.location
        return response

    def close(self):
        pass


def main():
    script = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location("schematic_probe_target", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    generator = module.ScientificSchematicGenerator(api_key=KEY)
    counts = {"redirect_cases": 0, "success_cases": 0, "redaction_cases": 0}

    # Even an accidental unmocked transport is unable to open a socket.
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")), \
         patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")), \
         patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")), \
         requests.Session() as session:
        session.trust_env = False
        session.adapters.clear()

        for endpoint in ("images", "chat/completions"):
            for status in range(300, 400):
                for location in ("https://redirect.invalid/" + KEY,
                                 "http://redirect.invalid/" + KEY, "/moved/" + KEY):
                    adapter = MemoryTransport(status, location, b"not JSON: " + KEY.encode())
                    session.mount("https://", adapter)
                    session.mount("http://", adapter)
                    with patch.object(module.requests, "post", side_effect=session.post):
                        try:
                            generator._post_request(endpoint, BODY)
                        except RuntimeError as error:
                            assert str(error) == f"API redirect refused (HTTP {status})", str(error)
                        else:
                            raise AssertionError(f"Accepted redirect {endpoint}/{status}")
                    assert len(adapter.seen) == 1, "Request replayed to redirect target"
                    assert adapter.seen[0].url == f"https://openrouter.ai/api/v1/{endpoint}"
                    counts["redirect_cases"] += 1

            adapter = MemoryTransport(200)
            session.mount("https://", adapter)
            with patch.object(module.requests, "post", side_effect=session.post):
                assert generator._post_request(endpoint, BODY) == {"synthetic": True}
            assert len(adapter.seen) == 1
            request = adapter.seen[0]
            assert request.headers["Authorization"] == "Bearer " + KEY
            assert json.loads(request.body) == BODY
            assert KEY not in request.body.decode()
            counts["success_cases"] += 1

            adapter = MemoryTransport(403, content=json.dumps({
                "error": {"message": "synthetic rejected " + KEY},
            }).encode())
            session.mount("https://", adapter)
            with patch.object(module.requests, "post", side_effect=session.post):
                try:
                    generator._post_request(endpoint, BODY)
                except RuntimeError as error:
                    assert KEY not in str(error)
                    assert "[redacted]" in str(error)
                else:
                    raise AssertionError("Accepted rejected request")
            counts["redaction_cases"] += 1

            with patch.object(module.requests, "post", side_effect=requests.ConnectionError(KEY)):
                try:
                    generator._post_request(endpoint, BODY)
                except RuntimeError as error:
                    assert KEY not in str(error)
                    assert "[redacted]" in str(error)
                else:
                    raise AssertionError("Accepted failed transport")
            counts["redaction_cases"] += 1
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
