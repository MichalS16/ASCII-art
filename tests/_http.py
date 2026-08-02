"""Shared mock-response helpers for tests."""

from unittest.mock import MagicMock

# sentinel distinguishing "not passed" (derive length from content) from an explicit content_length=None (omit the header)
_DERIVE_FROM_CONTENT = object()


def make_response(content=b"pixels", content_type="image/png", content_length=_DERIVE_FROM_CONTENT, url="http://example.com/image.png"):
    """Build a MagicMock standing in for a `requests` streaming response.

    content_length overrides the declared Content-Length header (default:
    derived from len(content)); pass None to omit the header entirely.
    url stands in for the final (post-redirect) response.url `requests` sets.
    """
    response = MagicMock()
    length = len(content) if content_length is _DERIVE_FROM_CONTENT else content_length
    response.headers = {"content-type": content_type} if length is None else {"content-length": str(length), "content-type": content_type}
    response.iter_content.return_value = [content]
    response.url = url
    return response
