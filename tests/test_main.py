"""Tests for main module - Bottle routes and application behavior."""

import json
import os
import unittest.mock as mock
import pytest
import bottle
from bottle import tob


# ── helpers ──────────────────────────────────────────────────────────────────

def make_environ(method="GET", path="/", query_string=""):
    """Build a minimal WSGI environ dict for bottle."""
    import io
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),   # text mode, as per WSGI spec
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }


def call_route(app, path, method="GET", query_string=""):
    """Invoke a bottle app route and return (status, body)."""
    environ = make_environ(method=method, path=path, query_string=query_string)
    responses = []

    def start_response(status, headers, exc_info=None):
        responses.append(status)

    body_iter = app(environ, start_response)
    body = b"".join(body_iter).decode()
    return responses[0], body


# ── sample feed data ──────────────────────────────────────────────────────────

def _make_feed_dict(n_flickr=5, n_youtube=5, n_old=30):
    """Create a feed dict with n_flickr + n_youtube + n_old entries."""
    feed = {}
    base_ts = "2021-{:02d}-01 00:00:00"

    for i in range(1, n_flickr + 1):
        fid = f"flickr-{i:020d}"
        feed[fid] = {
            "id": fid,
            "title": f"Flickr Album {i}",
            "link": f"https://flickr.com/{i}",
            "updated": base_ts.format(i % 12 + 1),
            "thumb": f"https://flickr.com/thumb{i}.jpg",
        }

    for i in range(1, n_youtube + 1):
        yid = f"youtube-video{i:010d}"
        feed[yid] = {
            "id": yid,
            "title": f"YouTube Video {i}",
            "link": f"https://youtu.be/video{i}",
            "updated": base_ts.format((i + 5) % 12 + 1),
            "thumb": f"https://ytimg.com/thumb{i}.jpg",
        }

    # Old items that should be pushed off the top-32 list
    for i in range(1, n_old + 1):
        oid = f"flickr-old{i:020d}"
        feed[oid] = {
            "id": oid,
            "title": f"Old Album {i}",
            "link": f"https://flickr.com/old{i}",
            "updated": "2010-01-01 00:00:00",
            "thumb": f"https://flickr.com/old_thumb{i}.jpg",
        }

    return feed


# ── import app after conftest has set env vars ────────────────────────────────

import main


# ── /feed.x tests ─────────────────────────────────────────────────────────────

class TestFeedEndpoint:
    """Tests for GET /feed.x."""

    def test_feed_returns_200_with_existing_file(self, tmp_path):
        """GET /feed.x returns 200 when feed.json exists."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = _make_feed_dict(n_flickr=2, n_youtube=2, n_old=0)
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            status, body = call_route(main.app, "/feed.x")

        assert status.startswith("200")

    def test_feed_returns_json(self, tmp_path):
        """GET /feed.x returns valid JSON."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = _make_feed_dict(n_flickr=2, n_youtube=2, n_old=0)
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            status, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        assert isinstance(parsed, dict)

    def test_feed_response_structure(self, tmp_path):
        """GET /feed.x response has 'data' and 'success' keys."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = _make_feed_dict(n_flickr=2, n_youtube=2, n_old=0)
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        assert "data" in parsed
        assert "success" in parsed
        assert parsed["success"] is True

    def test_feed_returns_empty_data_when_no_file(self, tmp_path):
        """GET /feed.x returns empty data list when feed.json does not exist."""
        feed_file = str(tmp_path / "no-such-file.json")

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        assert parsed["data"] == []
        assert parsed["success"] is True

    def test_feed_limits_to_32_items(self, tmp_path):
        """GET /feed.x returns at most 32 items."""
        feed_file = str(tmp_path / "feed.json")
        # 10 flickr + 10 youtube + 30 old = 50 total items
        feed_data = _make_feed_dict(n_flickr=10, n_youtube=10, n_old=30)
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        assert len(parsed["data"]) == 32

    def test_feed_sorted_by_updated_descending(self, tmp_path):
        """GET /feed.x returns items sorted newest-first."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "flickr-aaa": {
                "id": "flickr-aaa",
                "title": "Older",
                "link": "https://flickr.com/1",
                "updated": "2020-01-01 00:00:00",
                "thumb": "https://flickr.com/1.jpg",
            },
            "flickr-bbb": {
                "id": "flickr-bbb",
                "title": "Newer",
                "link": "https://flickr.com/2",
                "updated": "2022-01-01 00:00:00",
                "thumb": "https://flickr.com/2.jpg",
            },
            "youtube-ccc": {
                "id": "youtube-ccc",
                "title": "Middle",
                "link": "https://youtu.be/ccc",
                "updated": "2021-01-01 00:00:00",
                "thumb": "https://ytimg.com/ccc.jpg",
            },
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        items = parsed["data"]
        assert items[0]["id"] == "flickr-bbb"
        assert items[1]["id"] == "youtube-ccc"
        assert items[2]["id"] == "flickr-aaa"

    def test_feed_flickr_items_typed_as_picture(self, tmp_path):
        """GET /feed.x sets type='picture' for flickr- items."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "flickr-001": {
                "id": "flickr-001",
                "title": "Album",
                "link": "https://flickr.com/1",
                "updated": "2021-01-01 00:00:00",
                "thumb": "https://flickr.com/1.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        item = parsed["data"][0]
        assert item["type"] == "picture"

    def test_feed_youtube_items_typed_as_video(self, tmp_path):
        """GET /feed.x sets type='video' for youtube- items."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {
            "youtube-001": {
                "id": "youtube-001",
                "title": "Video",
                "link": "https://youtu.be/001",
                "updated": "2021-01-01 00:00:00",
                "thumb": "https://ytimg.com/1.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x")

        parsed = json.loads(body)
        item = parsed["data"][0]
        assert item["type"] == "video"

    def test_feed_jsonp_wraps_with_callback(self, tmp_path):
        """GET /feed.x?callback=fn returns JSONP-wrapped response."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {}
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x", query_string="callback=myFunc")

        assert body.startswith("myFunc(")
        assert body.endswith(");")

    def test_feed_jsonp_content_is_valid_json(self, tmp_path):
        """JSONP response contains valid JSON payload."""
        feed_file = str(tmp_path / "feed.json")
        feed_data = {}
        with open(feed_file, "w") as f:
            json.dump(feed_data, f)

        with mock.patch("main.FEED_FILE", feed_file):
            _, body = call_route(main.app, "/feed.x", query_string="callback=myFunc")

        # Strip the JSONP wrapper
        json_str = body[len("myFunc("):-len(");")]
        parsed = json.loads(json_str)
        assert "data" in parsed
        assert "success" in parsed


# ── /feed.r tests ─────────────────────────────────────────────────────────────

class TestFeedResetEndpoint:
    """Tests for GET /feed.r (cache reset)."""

    def test_feed_reset_deletes_file(self, tmp_path):
        """GET /feed.r removes feed.json when it exists."""
        feed_file = str(tmp_path / "feed.json")
        with open(feed_file, "w") as f:
            json.dump({}, f)
        assert os.path.exists(feed_file)

        with mock.patch("main.FEED_FILE", feed_file):
            call_route(main.app, "/feed.r")

        assert not os.path.exists(feed_file)

    def test_feed_reset_no_error_when_no_file(self, tmp_path):
        """GET /feed.r does not raise when feed.json does not exist."""
        feed_file = str(tmp_path / "no-file.json")
        assert not os.path.exists(feed_file)

        with mock.patch("main.FEED_FILE", feed_file):
            status, _ = call_route(main.app, "/feed.r")

        assert status.startswith("200")


# ── /healthz tests ─────────────────────────────────────────────────────────────

class TestHealthzEndpoint:
    """Tests for GET /healthz."""

    def test_healthz_returns_200(self):
        """GET /healthz returns 200."""
        status, body = call_route(main.app, "/healthz")
        assert status.startswith("200")

    def test_healthz_returns_json(self):
        """GET /healthz returns a JSON body."""
        _, body = call_route(main.app, "/healthz")
        parsed = json.loads(body)
        assert isinstance(parsed, dict)


# ── jsonp_response unit tests ─────────────────────────────────────────────────

class TestJsonpResponse:
    """Unit tests for jsonp_response()."""

    def test_returns_dict_without_callback(self):
        """Without ?callback, returns the dictionary as-is."""
        from main import jsonp_response

        mock_request = mock.MagicMock()
        mock_request.query.callback = None
        mock_response = mock.MagicMock()

        result = jsonp_response(mock_request, mock_response, {"key": "value"})
        assert result == {"key": "value"}

    def test_returns_jsonp_string_with_callback(self):
        """With ?callback=fn, returns JS function call string."""
        from main import jsonp_response

        mock_request = mock.MagicMock()
        mock_request.query.callback = "myCallback"
        mock_response = mock.MagicMock()

        result = jsonp_response(mock_request, mock_response, {"key": "value"})
        assert result == 'myCallback({"key": "value"});'

    def test_jsonp_sets_content_type(self):
        """JSONP response sets content_type to application/javascript."""
        from main import jsonp_response

        mock_request = mock.MagicMock()
        mock_request.query.callback = "myCallback"
        mock_response = mock.MagicMock()

        jsonp_response(mock_request, mock_response, {})
        assert mock_response.content_type == "application/javascript"
