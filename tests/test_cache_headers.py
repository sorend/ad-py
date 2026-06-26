"""Tests for HTTP cache headers (ETag, Cache-Control) on all routes."""

import io
import json
import os
import unittest.mock as mock

import main


# ── helper ────────────────────────────────────────────────────────────────────

def make_environ(method="GET", path="/", query_string="", if_none_match=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    if if_none_match:
        environ["HTTP_IF_NONE_MATCH"] = if_none_match
    return environ


def call_route_full(app, path, method="GET", query_string="", if_none_match=""):
    """Invoke a bottle app route and return (status, headers_dict, body).

    Header names in the returned dict are normalised to lowercase so tests are
    not sensitive to Bottle's title-casing (e.g. ``Etag`` vs ``ETag``).
    """
    environ = make_environ(
        method=method, path=path, query_string=query_string,
        if_none_match=if_none_match,
    )
    captured = []

    def start_response(status, headers, exc_info=None):
        captured.append((status, {k.lower(): v for k, v in headers}))

    body_iter = app(environ, start_response)
    body = b"".join(body_iter).decode()
    status, headers = captured[0]
    return status, headers, body


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestIndexCacheHeaders:

    def test_index_has_cache_control(self):
        """GET / includes a Cache-Control header."""
        _, headers, _ = call_route_full(main.app, "/")
        assert "cache-control" in headers

    def test_index_cache_control_is_no_cache(self):
        """GET / sets Cache-Control: no-cache so Cloudflare always revalidates."""
        _, headers, _ = call_route_full(main.app, "/")
        assert headers["cache-control"] == "no-cache"

    def test_index_has_etag(self):
        """GET / includes an ETag header."""
        _, headers, _ = call_route_full(main.app, "/")
        assert "etag" in headers

    def test_index_etag_contains_app_version(self):
        """GET / ETag is derived from the deployed app version."""
        with mock.patch("main.APP_VERSION", "1.2.3"):
            _, headers, _ = call_route_full(main.app, "/")
        assert "1.2.3" in headers["etag"]

    def test_index_returns_304_when_etag_matches(self):
        """GET / returns 304 when If-None-Match equals the current ETag."""
        with mock.patch("main.APP_VERSION", "test-ver"):
            _, headers, _ = call_route_full(main.app, "/")
            current_etag = headers["etag"]
            status, _, _ = call_route_full(main.app, "/", if_none_match=current_etag)
        assert status.startswith("304")

    def test_index_returns_200_when_etag_differs(self):
        """GET / returns 200 (not 304) when If-None-Match is stale."""
        status, _, _ = call_route_full(main.app, "/", if_none_match='"old-version"')
        assert status.startswith("200")


# ── GET /feed.x ───────────────────────────────────────────────────────────────

class TestFeedJsonCacheHeaders:

    def test_feed_x_has_cache_control(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.x")
        assert "cache-control" in headers

    def test_feed_x_cache_control_is_no_cache(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.x")
        assert headers["cache-control"] == "no-cache"

    def test_feed_x_has_etag(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.x")
        assert "etag" in headers

    def test_feed_x_etag_changes_when_feed_updated(self, tmp_path):
        """ETag for /feed.x changes when the feed file is rewritten."""
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, h1, _ = call_route_full(main.app, "/feed.x")
        # Advance mtime by 2 seconds to simulate the scheduler updating the feed.
        import time
        new_mtime = time.time() + 2
        os.utime(feed_file, (new_mtime, new_mtime))
        with mock.patch("main.FEED_FILE", feed_file):
            _, h2, _ = call_route_full(main.app, "/feed.x")
        assert h1["etag"] != h2["etag"]

    def test_feed_x_returns_304_when_etag_matches(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.x")
            current_etag = headers["etag"]
            status, _, _ = call_route_full(
                main.app, "/feed.x", if_none_match=current_etag
            )
        assert status.startswith("304")


# ── GET /feed.html ────────────────────────────────────────────────────────────

class TestFeedHtmlCacheHeaders:

    def test_feed_html_has_cache_control(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.html")
        assert "cache-control" in headers

    def test_feed_html_cache_control_is_no_cache(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.html")
        assert headers["cache-control"] == "no-cache"

    def test_feed_html_etag_changes_when_feed_updated(self, tmp_path):
        """ETag for /feed.html changes when the feed file is rewritten."""
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, h1, _ = call_route_full(main.app, "/feed.html")
        # Advance mtime by 2 seconds to simulate the scheduler updating the feed.
        import time
        new_mtime = time.time() + 2
        os.utime(feed_file, (new_mtime, new_mtime))
        with mock.patch("main.FEED_FILE", feed_file):
            _, h2, _ = call_route_full(main.app, "/feed.html")
        assert h1["etag"] != h2["etag"]

    def test_feed_html_returns_304_when_etag_matches(self, tmp_path):
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        with mock.patch("main.FEED_FILE", feed_file):
            _, headers, _ = call_route_full(main.app, "/feed.html")
            current_etag = headers["etag"]
            status, _, _ = call_route_full(
                main.app, "/feed.html", if_none_match=current_etag
            )
        assert status.startswith("304")


# ── GET /static/<file> ────────────────────────────────────────────────────────

class TestStaticCacheHeaders:

    def test_static_css_has_cache_control(self):
        """GET /static/front.css sets a Cache-Control header."""
        _, headers, _ = call_route_full(main.app, "/static/front.css")
        assert "cache-control" in headers

    def test_static_css_is_long_lived(self):
        """Static assets use a long max-age (versioned URLs bust the cache on deploy)."""
        _, headers, _ = call_route_full(main.app, "/static/front.css")
        cc = headers["cache-control"]
        assert "max-age=31536000" in cc
        assert "immutable" in cc
