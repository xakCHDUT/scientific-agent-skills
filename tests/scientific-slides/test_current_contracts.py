"""Offline API contract and local rendering regressions for the 2026 refresh."""
import base64
import json
from pathlib import Path
from unittest.mock import Mock, patch
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scientific-slides"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import generate_slide_image_ai as ai
import pdf_to_images
import slides_to_pdf
import validate_presentation


def test_generation_and_review_use_distinct_contracts(tmp_path):
    generator = ai.SlideImageGenerator(api_key="test-only-key")
    png = b"\x89PNG\r\n\x1a\npayload"
    ref = tmp_path / "style.png"
    ref.write_bytes(png)
    generated = Mock(status_code=200)
    generated.json.return_value = {"data": [{"b64_json": base64.b64encode(png).decode(), "media_type": "image/png"}]}
    reviewed = Mock(status_code=200)
    reviewed.json.return_value = {"choices": [{"message": {"content": "SCORE: 8\nVERDICT: ACCEPTABLE"}}]}
    with patch.object(ai.requests, "post", side_effect=[generated, reviewed]) as post:
        assert generator.generate_image("title", [str(ref)]) == png
        assert generator.review_image(str(ref), "title", 1).score == 8
    generation, review = post.call_args_list
    assert generation.args[0] == "https://openrouter.ai/api/v1/images"
    payload = generation.kwargs["json"]
    assert payload["aspect_ratio"] == "16:9" and payload["n"] == 1
    assert payload["prompt"] == "title" and "messages" not in payload
    assert payload["input_references"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert "output_format" not in payload
    assert generation.kwargs["headers"]["Authorization"] == "Bearer test-only-key"
    assert review.args[0].endswith("/chat/completions")
    assert review.kwargs["json"]["messages"][0]["content"][1]["type"] == "image_url"


def test_missing_reference_aborts_without_a_paid_request(tmp_path):
    generator = ai.SlideImageGenerator(api_key="test")
    with patch.object(ai.requests, "post") as post:
        assert generator.generate_image("slide", [str(tmp_path / "missing.png")]) is None
        assert generator.generate_image("slide", ["unused.png"] * 15) is None
        post.assert_not_called()


def test_refinement_failure_keeps_first_draft_and_records_quality(tmp_path):
    generator = ai.SlideImageGenerator(api_key="test")
    output = tmp_path / "slide.png"
    with patch.object(generator, "generate_image", side_effect=[b"first", None]) as draw, patch.object(generator, "review_image", return_value=ai.ReviewResult("too small", 3, True, True)):
        result = generator.generate_slide("slide", str(output))
    assert draw.call_count == 2
    assert output.read_bytes() == b"first"
    assert result["success"] and not result["quality_met"]
    assert result["termination_reason"] == "generation_failed"
    assert json.loads((tmp_path / "slide_review_log.json").read_text())["final_score"] == 3


def test_timeout_is_not_automatically_replayed(tmp_path):
    generator = ai.SlideImageGenerator(api_key="test")
    with patch.object(ai.requests, "post", side_effect=ai.requests.exceptions.Timeout) as post:
        result = generator.generate_slide("slide", str(tmp_path / "out.png"))
    assert post.call_count == 1
    assert not result["success"]
    assert result["termination_reason"] == "generation_failed"


@pytest.mark.parametrize("kwargs", [{"iterations": 0}, {"iterations": 3}, {"iterations": True}])
def test_invalid_iteration_count_rejected_before_generation(tmp_path, kwargs):
    generator = ai.SlideImageGenerator(api_key="test")
    with pytest.raises(ValueError):
        generator.generate_slide("slide", str(tmp_path / "out.png"), **kwargs)


def test_output_extension_must_match_png(tmp_path):
    with pytest.raises(ValueError, match=".png"):
        ai.SlideImageGenerator(api_key="test").generate_slide("slide", str(tmp_path / "out.jpg"))


def test_provider_error_does_not_echo_credential():
    generator = ai.SlideImageGenerator(api_key="secret-test")
    response = Mock(status_code=403)
    response.json.return_value = {"error": {"message": "rejected secret-test"}}
    with patch.object(ai.requests, "post", return_value=response), pytest.raises(RuntimeError) as error:
        generator._post_request("images", {"model": generator.image_model})
    assert "secret-test" not in str(error.value)


@pytest.mark.parametrize("endpoint", ["images", "chat/completions"])
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_api_redirect_refuses_to_replay_prompt_or_attachments(endpoint, status):
    generator = ai.SlideImageGenerator(api_key="secret-test")
    response = Mock(status_code=status)
    response.headers = {"Location": "https://untrusted.invalid/secret-test"}
    response.json.side_effect = ValueError("redirect body is not JSON")
    payload = {"model": "test", "prompt": "synthetic", "input_references": ["synthetic-image"]}
    with patch.object(ai.requests, "post", return_value=response) as post:
        with pytest.raises(RuntimeError, match="API redirect refused") as error:
            generator._post_request(endpoint, payload)
    assert post.call_args.kwargs["allow_redirects"] is False
    assert post.call_count == 1
    response.json.assert_not_called()
    assert "secret-test" not in str(error.value)
    assert "untrusted.invalid" not in str(error.value)


@pytest.mark.parametrize("endpoint", ["images", "chat/completions"])
@pytest.mark.parametrize("status", [307, 308])
@pytest.mark.parametrize("scheme", ["https", "http"])
def test_real_redirect_handling_never_reaches_second_origin(endpoint, status, scheme):
    """Run Requests' real redirect logic over an in-memory transport, never sockets."""
    import socket
    from requests.adapters import BaseAdapter
    from requests.models import Response

    class RedirectAdapter(BaseAdapter):
        def __init__(self):
            self.sent = []

        def send(self, request, **kwargs):
            self.sent.append(request)
            response = Response()
            response.request = request
            response.url = request.url
            response.status_code = status if len(self.sent) == 1 else 200
            response._content = b'{"ok": true}'
            response.headers["Location"] = f"{scheme}://untrusted.invalid/receive"
            return response

        def close(self):
            pass

    adapter = RedirectAdapter()
    generator = ai.SlideImageGenerator(api_key="dummy-key")
    payload = {"model": "test", "prompt": "synthetic", "input_references": ["synthetic-image"]}
    with ai.requests.Session() as session:
        session.trust_env = False
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        with patch.object(ai.requests, "post", side_effect=session.post), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network disabled")):
            with pytest.raises(RuntimeError, match="API redirect refused"):
                generator._post_request(endpoint, payload)
    assert len(adapter.sent) == 1
    assert adapter.sent[0].url == f"https://openrouter.ai/api/v1/{endpoint}"


def test_explicit_file_order_and_duplicate_identity_are_preserved(tmp_path):
    for name in ("title.png", "intro.png", "methods.png"):
        (tmp_path / name).touch()
    paths = [tmp_path / n for n in ("title.png", "intro.png", "methods.png")]
    assert slides_to_pdf.get_image_files([str(p) for p in paths] + [str(paths[0])]) == paths


@pytest.mark.parametrize("kwargs", [{"dpi": 0}, {"first_page": 0}, {"last_page": -1}, {"first_page": 3, "last_page": 2}])
def test_invalid_render_range_and_dpi_are_refused(kwargs):
    with pytest.raises(ValueError):
        pdf_to_images.PDFToImagesConverter("deck.pdf", "slide", **kwargs)


def test_range_beyond_pdf_is_refused_before_partial_render(tmp_path):
    import pymupdf
    source = tmp_path / "deck.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(source)
    converter = pdf_to_images.PDFToImagesConverter(str(source), str(tmp_path / "slide"), last_page=2)
    with pytest.raises(ValueError, match="1-1"):
        converter.convert()
    assert not list(tmp_path.glob("slide*"))


def test_legacy_ppt_has_actionable_failure(tmp_path):
    source = tmp_path / "legacy.ppt"
    source.write_bytes(b"legacy")
    result = validate_presentation.PresentationValidator(str(source)).validate()
    assert not result["valid"]
    assert "convert" in result["issues"][0]
