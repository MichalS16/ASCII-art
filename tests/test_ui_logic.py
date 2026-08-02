"""
Unit tests for ui_logic.py
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import requests

from ascii_art.ui_logic import (
    parse_custom_size,
    is_supported_image_content_type,
    is_fetchable_url,
    build_downloaded_image_filename,
    read_response_within_limit,
    check_url_is_image,
    fetch_and_save_image,
    truncate_filename_for_display,
    InvalidImageUrl,
    MAX_DOWNLOAD_BYTES,
)

from _http import make_response
from _tempcwd import IsolatedTempCwdMixin


class ParseCustomSizeTests(unittest.TestCase):
    def test_valid_size(self):
        # "500x400" parses into [500, 400]
        self.assertEqual(parse_custom_size("500x400"), [500, 400])

    def test_missing_separator_raises(self):
        # no "x" separator must raise
        with self.assertRaises(ValueError):
            parse_custom_size("500400")

    def test_non_numeric_raises(self):
        # non-numeric width/height must raise
        with self.assertRaises(ValueError):
            parse_custom_size("abcxdef")

    def test_zero_width_raises(self):
        # zero width must raise (only positive sizes are valid)
        with self.assertRaises(ValueError):
            parse_custom_size("0x400")

    def test_negative_width_raises(self):
        # negative width must raise
        with self.assertRaises(ValueError):
            parse_custom_size("-500x400")

    def test_negative_height_raises(self):
        # negative height must raise
        with self.assertRaises(ValueError):
            parse_custom_size("500x-400")

    def test_too_many_parts_raises(self):
        # more than one "x" separator must raise
        with self.assertRaises(ValueError):
            parse_custom_size("1x2x3")


class TruncateFilenameForDisplayTests(unittest.TestCase):
    def test_short_filename_is_unchanged(self):
        # a filename already within the length limit is returned as-is
        self.assertEqual(truncate_filename_for_display("short.png"), "short.png")

    def test_long_filename_keeps_extension(self):
        # truncating a long filename must still keep its extension intact
        result = truncate_filename_for_display("this-is-an-extremely-long-filename-that-someone-picked.png")
        self.assertTrue(result.endswith(".png"))
        self.assertLessEqual(len(result), 24)

    def test_long_filename_without_extension_is_truncated(self):
        # a long filename with no extension is truncated with a trailing ellipsis
        result = truncate_filename_for_display("no_extension_but_really_long_filename_here_yes")
        self.assertLessEqual(len(result), 24)
        self.assertTrue(result.endswith("…"))

    def test_result_never_exceeds_max_length_even_with_long_extension(self):
        # a long extension must not push the result past the length limit
        result = truncate_filename_for_display("a" * 30 + ".verylongextension")
        self.assertLessEqual(len(result), 24)

    def test_extension_alone_longer_than_max_length_falls_back_to_plain_truncation(self):
        # an extension longer than the whole limit falls back to plain truncation
        result = truncate_filename_for_display("x." + "e" * 30)
        self.assertLessEqual(len(result), 24)
        self.assertTrue(result.endswith("…"))

    def test_custom_max_length_is_respected(self):
        # an explicit max_length overrides the default 24-character limit
        result = truncate_filename_for_display("this-is-a-longer-filename.png", max_length=12)
        self.assertLessEqual(len(result), 12)

    def test_exactly_at_max_length_is_unchanged(self):
        # a filename exactly at the limit is returned unchanged, not truncated
        name = "a" * 24
        self.assertEqual(truncate_filename_for_display(name), name)


class ContentTypeTests(unittest.TestCase):
    def test_png_is_supported(self):
        # image/png is a supported content-type
        self.assertTrue(is_supported_image_content_type("image/png"))

    def test_webp_is_supported(self):
        # image/webp is supported since some CDNs re-encode requested .jpg/.png URLs as WebP
        self.assertTrue(is_supported_image_content_type("image/webp"))

    def test_pdf_is_not_supported(self):
        # non-image content-types are rejected
        self.assertFalse(is_supported_image_content_type("application/pdf"))

    def test_none_is_not_supported(self):
        # a missing content-type header is rejected, not treated as valid
        self.assertFalse(is_supported_image_content_type(None))

    def test_content_type_with_charset_parameter_is_supported(self):
        # real servers often send a charset/boundary parameter after the MIME type
        self.assertTrue(is_supported_image_content_type("image/png; charset=binary"))

    def test_content_type_is_case_insensitive(self):
        # some servers send non-lowercase content-type headers
        self.assertTrue(is_supported_image_content_type("Image/PNG"))


class IsFetchableUrlTests(unittest.TestCase):
    def test_http_url_is_fetchable(self):
        # plain http:// URLs are fetchable
        self.assertTrue(is_fetchable_url("http://example.com/cat.png"))

    def test_https_url_is_fetchable(self):
        # https:// URLs are fetchable
        self.assertTrue(is_fetchable_url("https://example.com/cat.png"))

    def test_file_scheme_is_rejected(self):
        # file:// URLs are rejected to prevent reading local files
        self.assertFalse(is_fetchable_url("file:///etc/passwd"))

    def test_data_scheme_is_rejected(self):
        # data: URLs are rejected
        self.assertFalse(is_fetchable_url("data:image/png;base64,aGVsbG8="))

    def test_ftp_scheme_is_rejected(self):
        # ftp:// URLs are rejected
        self.assertFalse(is_fetchable_url("ftp://example.com/cat.png"))

    def test_scheme_without_host_is_rejected(self):
        # a URL with no host is rejected even with an allowed scheme
        self.assertFalse(is_fetchable_url("http:///cat.png"))

    def test_malformed_url_is_rejected(self):
        # a string that isn't a URL at all is rejected
        self.assertFalse(is_fetchable_url("not a url"))


class BuildDownloadedImageFilenameTests(IsolatedTempCwdMixin, unittest.TestCase):
    def test_extracts_filename_from_url(self):
        # the URL's last path segment is used as the saved filename
        result = build_downloaded_image_filename("https://example.com/path/cat.png")
        self.assertEqual(result, os.path.join("Results", "cat.png"))

    def test_uses_custom_results_dir(self):
        # an explicit results_dir is used instead of the default Results/
        result = build_downloaded_image_filename("https://example.com/cat.png", results_dir="out")
        self.assertEqual(result, os.path.join("out", "cat.png"))

    def test_strips_query_string(self):
        # a "?..." query string must not end up as part of the saved filename
        result = build_downloaded_image_filename("https://example.com/cat.png?size=large")
        self.assertEqual(result, os.path.join("Results", "cat.png"))

    def test_rejects_unix_path_traversal(self):
        # a "../" path-traversal attempt must not escape Results/ ("passwd" also triggers the timestamp fallback below)
        result = build_downloaded_image_filename("https://evil.com/../../etc/passwd")
        self.assertEqual(os.path.dirname(result), "Results")
        self.assertNotIn("..", result)

    def test_rejects_windows_path_traversal(self):
        # a Windows-style "..\\" path-traversal attempt is stripped down to just the final segment
        result = build_downloaded_image_filename("https://evil.com/..\\..\\windows\\win.ini")
        self.assertEqual(result, os.path.join("Results", "win.ini"))

    def test_falls_back_to_timestamped_name_when_url_path_is_empty(self):
        # a URL with no path segment at all falls back to a timestamped name with the right extension
        result = build_downloaded_image_filename("https://example.com/", content_type="image/png")
        name = os.path.basename(result)
        self.assertTrue(name.startswith("downloaded-image-"))
        self.assertTrue(name.endswith(".png"))

    def test_url_path_segment_with_no_extension_falls_back_to_timestamped_name(self):
        # a CDN URL with a generic, extension-less path segment (e.g. gstatic's "/images") also gets a timestamped name
        result = build_downloaded_image_filename(
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQEpdHPlukaikwyFGeN-AFGLCT2HCjRtQxZRQTrlcgQ5w&s=10",
            content_type="image/jpeg",
        )
        name = os.path.basename(result)
        self.assertTrue(name.startswith("downloaded-image-"))
        self.assertTrue(name.endswith(".jpg"))

    def test_timestamped_name_with_unknown_content_type_has_no_extension(self):
        # an unrecognized/missing content-type produces a timestamped name with no extension, not a wrong one
        result = build_downloaded_image_filename("https://example.com/", content_type=None)
        name = os.path.basename(result)
        self.assertTrue(name.startswith("downloaded-image-"))
        self.assertFalse(name.endswith("."))

    def test_content_type_with_charset_parameter_still_picks_the_right_extension(self):
        # a content-type with trailing params (e.g. "; charset=binary") must still resolve its extension,
        # matching the normalization is_supported_image_content_type already applies to the same header
        result = build_downloaded_image_filename("https://example.com/", content_type="image/png; charset=binary")
        name = os.path.basename(result)
        self.assertTrue(name.endswith(".png"))

    def test_content_type_with_different_case_still_picks_the_right_extension(self):
        # a non-lowercase content-type (e.g. "Image/PNG") must still resolve its extension
        result = build_downloaded_image_filename("https://example.com/", content_type="Image/PNG")
        name = os.path.basename(result)
        self.assertTrue(name.endswith(".png"))


class ReadResponseWithinLimitTests(unittest.TestCase):
    def test_reads_full_body_within_limit(self):
        # a response within the size limit is read and returned in full
        response = make_response(content=b"hello world")
        self.assertEqual(read_response_within_limit(response), b"hello world")

    def test_rejects_declared_content_length_over_limit(self):
        # a declared Content-Length over the limit raises before any streaming happens
        response = make_response(content=b"irrelevant", content_length=MAX_DOWNLOAD_BYTES + 1)
        with self.assertRaises(ValueError):
            read_response_within_limit(response)

    def test_rejects_streamed_body_over_limit_when_header_absent_or_wrong(self):
        # no declared Content-Length; an oversized streamed body is still caught and rejected
        response = make_response(content=b"x" * (MAX_DOWNLOAD_BYTES + 1), content_length=None)
        with self.assertRaises(ValueError):
            read_response_within_limit(response)

    def test_custom_limit_is_respected(self):
        # an explicit max_bytes override is enforced instead of the default limit
        response = make_response(content=b"x" * 100)
        with self.assertRaises(ValueError):
            read_response_within_limit(response, max_bytes=10)

    def test_malformed_content_length_header_raises_value_error(self):
        # a non-numeric Content-Length (a malformed/hostile server response) must
        # still raise ValueError, the same type callers already catch, rather than
        # some other exception type slipping through uncaught
        response = make_response(content=b"irrelevant", content_length="not-a-number")
        with self.assertRaises(ValueError):
            read_response_within_limit(response)


class CheckUrlIsImageTests(unittest.TestCase):
    def _response(self, content_type="image/png", url="https://example.com/cat.png"):
        response = MagicMock()
        response.headers = {"content-type": content_type}
        response.url = url
        return response

    def test_true_for_reachable_image_url(self):
        # a reachable URL with a supported image content-type returns True, via a HEAD request only
        head = MagicMock(return_value=self._response())
        self.assertTrue(check_url_is_image("https://example.com/cat.png", head=head))
        head.assert_called_once_with("https://example.com/cat.png", timeout=5, allow_redirects=True)

    def test_false_for_non_http_scheme_without_calling_head(self):
        # a non-http(s) URL is rejected up front, without making any network request
        head = MagicMock()
        self.assertFalse(check_url_is_image("file:///etc/passwd", head=head))
        head.assert_not_called()

    def test_false_for_unsupported_content_type(self):
        # a reachable URL with a non-image content-type returns False
        head = MagicMock(return_value=self._response(content_type="text/html"))
        self.assertFalse(check_url_is_image("https://example.com/page.html", head=head))

    def test_false_on_request_exception(self):
        # a network error is treated as "not valid", not raised to the caller
        head = MagicMock(side_effect=requests.RequestException("boom"))
        self.assertFalse(check_url_is_image("https://example.com/cat.png", head=head))

    def test_uses_default_requests_head_when_not_injected(self):
        # without an injected head callable, the real requests.head is used
        with patch("ascii_art.ui_logic.requests.head", return_value=self._response()) as mock_head:
            result = check_url_is_image("https://example.com/cat.png")
        mock_head.assert_called_once_with("https://example.com/cat.png", timeout=5, allow_redirects=True)
        self.assertTrue(result)

    def test_redirect_to_non_http_url_is_rejected(self):
        # a redirect chain landing on a non-http(s) URL (e.g. file://) must not validate
        head = MagicMock(return_value=self._response(url="file:///etc/passwd"))
        self.assertFalse(check_url_is_image("https://example.com/redirect", head=head))


class FetchAndSaveImageTests(IsolatedTempCwdMixin, unittest.TestCase):
    def test_saves_image_and_returns_filename(self):
        # a valid image URL is downloaded, saved to Results/, and its path returned
        get = MagicMock(return_value=make_response())
        result = fetch_and_save_image("https://example.com/cat.png", get=get)
        self.assertEqual(result, os.path.join("Results", "cat.png"))
        with open(result, "rb") as f:
            self.assertEqual(f.read(), b"pixels")

    def test_non_http_scheme_raises_without_calling_get(self):
        # a non-http(s) URL raises InvalidImageUrl without making any network request
        get = MagicMock()
        with self.assertRaises(InvalidImageUrl):
            fetch_and_save_image("file:///etc/passwd", get=get)
        get.assert_not_called()

    def test_request_exception_raises_invalid_image_url(self):
        # a network-level failure is wrapped into InvalidImageUrl
        get = MagicMock(side_effect=requests.RequestException("boom"))
        with self.assertRaises(InvalidImageUrl):
            fetch_and_save_image("https://example.com/cat.png", get=get)

    def test_unsupported_content_type_raises(self):
        # a response with a non-image content-type raises InvalidImageUrl
        get = MagicMock(return_value=make_response(content_type="text/html"))
        with self.assertRaises(InvalidImageUrl):
            fetch_and_save_image("https://example.com/cat.html", get=get)

    def test_oversized_download_raises(self):
        # a response declaring a Content-Length over the limit raises InvalidImageUrl
        response = make_response(content_length=MAX_DOWNLOAD_BYTES + 1)
        get = MagicMock(return_value=response)
        with self.assertRaises(InvalidImageUrl):
            fetch_and_save_image("https://example.com/huge.png", get=get)

    def test_uses_default_requests_get_when_not_injected(self):
        # without an injected get callable, the real requests.get is used with the expected arguments
        with patch("ascii_art.ui_logic.requests.get", return_value=make_response()) as mock_get:
            result = fetch_and_save_image("https://example.com/cat.png")
        mock_get.assert_called_once_with("https://example.com/cat.png", timeout=10, stream=True)
        self.assertEqual(result, os.path.join("Results", "cat.png"))

    def test_redirect_to_non_http_url_raises(self):
        # a redirect chain landing on a non-http(s) URL (e.g. file://) must not be saved
        get = MagicMock(return_value=make_response(url="file:///etc/passwd"))
        with self.assertRaises(InvalidImageUrl):
            fetch_and_save_image("https://example.com/redirect", get=get)

    def test_url_with_no_filename_in_path_gets_a_timestamped_name(self):
        # a URL with a generic, extension-less path segment gets a timestamped name end-to-end
        get = MagicMock(return_value=make_response(content_type="image/jpeg"))
        result = fetch_and_save_image("https://encrypted-tbn0.gstatic.com/images?q=tbn:xyz", get=get)
        name = os.path.basename(result)
        self.assertTrue(name.startswith("downloaded-image-"))
        self.assertTrue(name.endswith(".jpg"))


if __name__ == "__main__":
    unittest.main()
