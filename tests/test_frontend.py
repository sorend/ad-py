"""Tests for frontend routes - index page, static files, feed HTML fragment, 404."""

import json
import os
import unittest.mock as mock
import pytest


# ── helpers (same pattern as test_main.py) ────────────────────────────────────

def make_environ(method="GET", path="/", query_string=""):
    import io
    return {
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


def call_route(app, path, method="GET", query_string=""):
    environ = make_environ(method=method, path=path, query_string=query_string)
    responses = []

    def start_response(status, headers, exc_info=None):
        responses.append(status)

    body_iter = app(environ, start_response)
    body = b"".join(body_iter).decode()
    return responses[0], body


def call_route_bytes(app, path, method="GET", query_string=""):
    """Like call_route but returns raw bytes body (for binary responses)."""
    environ = make_environ(method=method, path=path, query_string=query_string)
    responses = []

    def start_response(status, headers, exc_info=None):
        responses.append(status)

    body_iter = app(environ, start_response)
    body = b"".join(body_iter)
    return responses[0], body


import main


# ── GET / ──────────────────────────────────────────────────────────────────────

class TestIndexRoute:
    """Tests for GET /."""

    def test_index_returns_200(self):
        """GET / returns HTTP 200."""
        status, _ = call_route(main.app, "/")
        assert status.startswith("200")

    def test_index_returns_html(self):
        """GET / response body is an HTML document."""
        _, body = call_route(main.app, "/")
        assert "<!doctype html" in body.lower()

    def test_index_contains_htmx_script(self):
        """GET / page loads htmx from CDN."""
        _, body = call_route(main.app, "/")
        assert "htmx.org" in body

    def test_index_has_feed_hx_get(self):
        """GET / page has an element that triggers htmx load for /feed.html."""
        _, body = call_route(main.app, "/")
        assert 'hx-get="/feed.html"' in body

    def test_index_has_hx_trigger_load(self):
        """GET / page triggers the feed request on page load."""
        _, body = call_route(main.app, "/")
        assert 'hx-trigger="load"' in body

    def test_index_links_to_static_css(self):
        """GET / page references the static CSS file."""
        _, body = call_route(main.app, "/")
        assert "/static/front.css" in body

    def test_index_has_page_title(self):
        """GET / page title contains 'Atmakuri Davidsen'."""
        _, body = call_route(main.app, "/")
        assert "Atmakuri Davidsen" in body


# ── GET /feed.html ─────────────────────────────────────────────────────────────

class TestFeedHtmlEndpoint:
    """Tests for GET /feed.html (htmx partial)."""

    def test_feed_html_returns_200(self, tmp_path):
        """GET /feed.html returns 200."""
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)

        with mock.patch("main.FEED_FILE", feed_file):
            status, _ = call_route(main.app, "/feed.html")

        assert status.startswith("200")

    def test_feed_html_empty_when_no_file(self, tmp_path):
        """GET /feed.html returns the empty-state message when no feed file exists."""
        feed_file = str(tmp_path / "no-file.json")

        with mock.patch("main.FEED_FILE", feed_file):
            status, body = call_route(main.app, "/feed.html")

        assert status.startswith("200")
        assert "No items available" in body

    def test_feed_html_renders_items(self, tmp_path):
        """GET /feed.html renders a .fi div for each feed item."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "flickr-001": {
                "id": "flickr-001",
                "title": "Nice Album",
                "link": "https://flickr.com/1",
                "updated": "2022-03-01 00:00:00",
                "thumb": "https://flickr.com/1.jpg",
            },
            "youtube-002": {
                "id": "youtube-002",
                "title": "Cool Video",
                "link": "https://youtu.be/002",
                "updated": "2022-04-01 00:00:00",
                "thumb": "https://ytimg.com/2.jpg",
            },
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.html")

        assert body.count('class="fi"') == 2
        assert "Nice Album" in body
        assert "Cool Video" in body

    def test_feed_html_flickr_item_has_picture_class(self, tmp_path):
        """GET /feed.html gives flickr items a 'picture' CSS class."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "flickr-001": {
                "id": "flickr-001",
                "title": "Album",
                "link": "https://flickr.com/1",
                "updated": "2022-03-01 00:00:00",
                "thumb": "https://flickr.com/1.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.html")

        assert 'class="picture"' in body

    def test_feed_html_youtube_item_has_video_class(self, tmp_path):
        """GET /feed.html gives youtube items a 'video' CSS class."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "youtube-001": {
                "id": "youtube-001",
                "title": "Video",
                "link": "https://youtu.be/001",
                "updated": "2022-03-01 00:00:00",
                "thumb": "https://ytimg.com/1.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.html")

        assert 'class="video"' in body

    def test_feed_html_limits_to_32_items(self, tmp_path):
        """GET /feed.html renders at most 32 items."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            f"flickr-{i:04d}": {
                "id": f"flickr-{i:04d}",
                "title": f"Album {i}",
                "link": f"https://flickr.com/{i}",
                "updated": f"202{i % 3}-{(i % 12) + 1:02d}-01 00:00:00",
                "thumb": f"https://flickr.com/{i}.jpg",
            }
            for i in range(1, 51)
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.html")

        assert body.count('class="fi"') == 32

    def test_feed_html_no_jquery_or_handlebars(self, tmp_path):
        """GET /feed.html does not include jQuery or Handlebars (legacy deps removed)."""
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.html")

        assert "jquery" not in body.lower()
        assert "handlebars" not in body.lower()


# ── GET /static/<file> ─────────────────────────────────────────────────────────

class TestStaticFiles:
    """Tests for GET /static/<filepath>."""

    def test_static_css_returns_200(self):
        """GET /static/front.css returns 200."""
        status, _ = call_route(main.app, "/static/front.css")
        assert status.startswith("200")

    def test_static_css_content_type(self):
        """GET /static/front.css has a CSS content type."""
        environ = make_environ(path="/static/front.css")
        headers_captured = []

        def start_response(status, headers, exc_info=None):
            headers_captured.extend(headers)

        main.app(environ, start_response)
        content_types = [v for k, v in headers_captured if k.lower() == "content-type"]
        assert any("css" in ct for ct in content_types)

    def test_static_family_png_returns_200(self):
        """GET /static/family.png returns 200."""
        status, _ = call_route_bytes(main.app, "/static/family.png")
        assert status.startswith("200")

    def test_static_header_jpg_returns_200(self):
        """GET /static/header_frontpage.jpg returns 200."""
        status, _ = call_route_bytes(main.app, "/static/header_frontpage.jpg")
        assert status.startswith("200")

    def test_static_nonexistent_returns_404(self):
        """GET /static/nonexistent.file returns 404."""
        status, _ = call_route(main.app, "/static/nonexistent.file")
        assert status.startswith("404")


# ── 404 handler ────────────────────────────────────────────────────────────────

class TestNotFound:
    """Tests for the custom 404 error page."""

    def test_unknown_route_returns_404(self):
        """GET /this/does/not/exist returns 404."""
        status, _ = call_route(main.app, "/this/does/not/exist")
        assert status.startswith("404")

    def test_404_returns_html(self):
        """404 response is an HTML document."""
        _, body = call_route(main.app, "/no-such-page")
        assert "<!doctype html" in body.lower()

    def test_404_contains_not_here_message(self):
        """404 page contains the 'not here anymore' message."""
        _, body = call_route(main.app, "/no-such-page")
        assert "not here anymore" in body.lower()
