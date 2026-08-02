"""
Pure helper logic for user_interface.py, kept free of tkinter/customtkinter
dependencies so it can be unit tested directly.
"""

import os
from datetime import datetime
from urllib.parse import urlparse

import requests

from ascii_art.ascii_generator import RESULTS_DIR
from ascii_art.paths import ensure_dir_and_join

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_URL_SCHEMES = ("http", "https")

CONTENT_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
# supported image MIME types; derived from CONTENT_TYPE_EXTENSIONS so the two
# can't drift out of sync when a new format is added
IMAGE_CONTENT_TYPES = tuple(CONTENT_TYPE_EXTENSIONS)


def truncate_filename_for_display(filename, max_length=24):
    """Shorten filename to at most max_length characters for UI display.

    Keeps the extension and a lead-in from the start (e.g.
    "a-very-long-filenam….png"), rather than wrapping or overflowing a
    fixed-width label - long PC filenames would otherwise blow past the
    label's box and shift the surrounding layout.
    """
    if len(filename) <= max_length:
        return filename

    stem, dot, extension = filename.rpartition(".")
    if not dot:
        return filename[: max_length - 1] + "…"

    # keep the extension intact; truncate only the stem
    available_for_stem = max_length - len(extension) - 2  # "…" + "."
    if available_for_stem <= 0:
        return filename[: max_length - 1] + "…"

    return stem[:available_for_stem] + "…." + extension


def is_fetchable_url(url):
    """Return True only for http(s) URLs with a host.

    Rejects file://, data:, ftp:// and similar schemes so a malicious or
    mistaken URL can't make the app read local files or hit non-http
    services instead of downloading an image.

    Does not resolve the host or reject loopback/link-local/private IP
    ranges (e.g. 127.0.0.1, 169.254.169.254) - a user of this single-user
    desktop GUI supplies their own URL, so full SSRF hardening against their
    own reachable network is accepted as out of scope for this tool.
    """
    parsed = urlparse(url)
    return parsed.scheme in ALLOWED_URL_SCHEMES and bool(parsed.netloc)


def parse_custom_size(raw_input):
    """Parse a 'widthxheight' string into [width, height] of positive ints.

    Raises ValueError if the input is malformed or non-positive.
    """
    parts = raw_input.split("x")
    if len(parts) != 2:
        raise ValueError("Expected format widthxheight")

    size = [int(part) for part in parts]
    if size[0] <= 0 or size[1] <= 0:
        raise ValueError("Width and height must be positive")

    return size


def _normalize_content_type(content_type):
    """Strip any trailing parameters (e.g. "; charset=binary") and lowercase
    content_type, since real servers commonly send both variations. Returns
    None if content_type is None."""
    if content_type is None:
        return None
    return content_type.split(";", 1)[0].strip().lower()


def is_supported_image_content_type(content_type):
    """Return True if content_type is one of the recognized image MIME types.

    Ignores case and any trailing parameters (e.g. "image/png; charset=binary"
    or "Image/PNG"), since real servers commonly send both.
    """
    return _normalize_content_type(content_type) in IMAGE_CONTENT_TYPES


def build_downloaded_image_filename(url, content_type=None, results_dir=RESULTS_DIR):
    """Build a safe destination path for a downloaded image, creating results_dir.

    Uses only the final path segment of the URL and strips any directory
    components so a malicious URL (e.g. containing ../ or ..\\) cannot
    write outside results_dir.
    """
    url_path = url.split("?")[0].split("#")[0]
    candidate_name = os.path.basename(url_path.replace("\\", "/"))

    if candidate_name and "." in candidate_name:
        safe_name = candidate_name
    else:
        extension = CONTENT_TYPE_EXTENSIONS.get(_normalize_content_type(content_type), "")
        safe_name = "downloaded-image-" + datetime.now().strftime("%Y%m%d-%H%M%S") + extension

    return ensure_dir_and_join(results_dir, safe_name)


def read_response_within_limit(response, max_bytes=MAX_DOWNLOAD_BYTES):
    """Read a streaming `requests` response body, enforcing a byte cap.

    Raises ValueError if the declared Content-Length or the actual streamed
    size exceeds max_bytes, guarding against a malicious/huge response being
    fully buffered into memory and written to disk.
    """
    content_length = response.headers.get("content-length")
    if content_length is not None and int(content_length) > max_bytes:
        raise ValueError("Download exceeds the maximum allowed size")

    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("Download exceeds the maximum allowed size")
        chunks.append(chunk)
    return b"".join(chunks)


class InvalidImageUrl(Exception):
    """Raised by fetch_and_save_image when a URL can't be used as an image source.

    Covers a rejected scheme/host, an unsupported content-type, an oversized
    download, and network-level failures alike, so callers only need to
    handle one exception type to drive a "show an error, let the user retry"
    flow.
    """


def check_url_is_image(url, head=None):
    """Return True if url is fetchable and its Content-Type is a supported
    image type, without downloading the body.

    Used for live "does this look valid" UI feedback while the user is still
    typing, so it deliberately does not download/save anything (unlike
    fetch_and_save_image) and swallows network errors as "not valid" rather
    than raising, since a transient failure here shouldn't surface as an
    error dialog - the user hasn't clicked Generate yet.
    """
    if head is None:
        head = requests.head

    if not is_fetchable_url(url):
        return False

    try:
        response = head(url, timeout=5, allow_redirects=True)
    except requests.RequestException:
        return False

    if not is_fetchable_url(response.url):
        return False

    return is_supported_image_content_type(response.headers.get("content-type"))


def fetch_and_save_image(url, get=None, results_dir=RESULTS_DIR):
    """Validate, download, and save the image at url. Returns the saved path.

    Runs the full validate-then-fetch-then-save pipeline that used to be
    interleaved with GUI/error-dialog logic in user_interface.py's generate().
    Raises InvalidImageUrl for any failure (bad scheme, wrong content-type,
    oversized body, or a network error) so the caller only has one case to
    handle instead of three separate checks plus a try/except.
    """
    if get is None:
        get = requests.get

    if not is_fetchable_url(url):
        raise InvalidImageUrl(f"Not a fetchable http(s) URL: {url!r}")

    try:
        response = get(url, timeout=10, stream=True)
    except requests.RequestException as error:
        raise InvalidImageUrl(f"Request failed: {error}") from error

    # a redirect could have led somewhere no longer http(s)-with-a-host
    # (e.g. an internal address); re-check the URL actually fetched
    if not is_fetchable_url(response.url):
        raise InvalidImageUrl(f"Redirected to a non-fetchable URL: {response.url!r}")

    content_type = response.headers.get("content-type")
    if not is_supported_image_content_type(content_type):
        raise InvalidImageUrl(f"Unsupported content-type for {url!r}")

    try:
        content = read_response_within_limit(response)
    except ValueError as error:
        raise InvalidImageUrl(str(error)) from error

    filename = build_downloaded_image_filename(url, content_type=content_type, results_dir=results_dir)
    with open(filename, "wb") as file:
        file.write(content)
    return filename
