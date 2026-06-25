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


# ── year_month derivation tests ───────────────────────────────────────────────

class TestYearMonthDerivation:
    """Tests for year_month field computed by _load_feed()."""

    def _write_feed(self, feed_file, items_by_id):
        with open(feed_file, "w") as f:
            json.dump(items_by_id, f)

    def test_year_month_present_in_each_item(self, tmp_path):
        """Every item returned by _load_feed() has a 'year_month' key."""
        feed_file = str(tmp_path / "feed.json")
        self._write_feed(feed_file, {
            "flickr-001": {
                "id": "flickr-001", "title": "Album",
                "link": "https://f.com/1", "updated": "2021-06-01 00:00:00",
                "thumb": "https://f.com/1.jpg",
            }
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        assert "year_month" in items[0]

    def test_year_month_from_title_date(self, tmp_path):
        """year_month uses title_date when present."""
        feed_file = str(tmp_path / "feed.json")
        self._write_feed(feed_file, {
            "flickr-001": {
                "id": "flickr-001", "title": "2022 August holiday",
                "link": "https://f.com/1", "updated": "2021-06-01 00:00:00",
                "thumb": "https://f.com/1.jpg",
                "title_date": "2022-08",
                "median_taken_date": "2020-01-01 00:00:00",
            }
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        assert items[0]["year_month"] == "2022-08"

    def test_year_month_from_median_taken_when_no_title_date(self, tmp_path):
        """year_month uses median_taken_date when title_date is absent."""
        feed_file = str(tmp_path / "feed.json")
        self._write_feed(feed_file, {
            "flickr-001": {
                "id": "flickr-001", "title": "Plain Album",
                "link": "https://f.com/1", "updated": "2019-01-01 00:00:00",
                "thumb": "https://f.com/1.jpg",
                "title_date": None,
                "median_taken_date": "2021-07-15 12:00:00",
            }
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        assert items[0]["year_month"] == "2021-07"

    def test_year_month_from_updated_when_no_title_or_median(self, tmp_path):
        """year_month falls back to updated when title_date and median_taken_date are absent."""
        feed_file = str(tmp_path / "feed.json")
        self._write_feed(feed_file, {
            "youtube-001": {
                "id": "youtube-001", "title": "A video",
                "link": "https://youtu.be/001", "updated": "2023-09-05 08:00:00",
                "thumb": "https://ytimg.com/1.jpg",
                # no title_date, no median_taken_date
            }
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        assert items[0]["year_month"] == "2023-09"

    def test_year_month_none_median_falls_back_to_updated(self, tmp_path):
        """Explicit None for median_taken_date correctly falls back to updated."""
        feed_file = str(tmp_path / "feed.json")
        self._write_feed(feed_file, {
            "flickr-001": {
                "id": "flickr-001", "title": "Album",
                "link": "https://f.com/1", "updated": "2022-03-01 00:00:00",
                "thumb": "https://f.com/1.jpg",
                "title_date": None,
                "median_taken_date": None,
            }
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        assert items[0]["year_month"] == "2022-03"

    def test_feed_sorted_by_year_month_descending(self, tmp_path):
        """Items are sorted by year_month descending (title_date used when present)."""
        feed_file = str(tmp_path / "feed.json")
        # title_date "2023-08" > updated "2022-01" > updated "2020-06"
        self._write_feed(feed_file, {
            "flickr-old": {
                "id": "flickr-old", "title": "Old album",
                "link": "https://f.com/old", "updated": "2020-06-01 00:00:00",
                "thumb": "https://f.com/old.jpg",
                "title_date": None, "median_taken_date": None,
            },
            "youtube-mid": {
                "id": "youtube-mid", "title": "Mid video",
                "link": "https://youtu.be/mid", "updated": "2022-01-01 00:00:00",
                "thumb": "https://ytimg.com/mid.jpg",
            },
            "flickr-future": {
                "id": "flickr-future", "title": "Future album",
                "link": "https://f.com/future", "updated": "2018-01-01 00:00:00",
                "thumb": "https://f.com/future.jpg",
                "title_date": "2023-08",  # overrides updated
                "median_taken_date": None,
            },
        })

        with mock.patch("main.FEED_FILE", feed_file):
            from main import _load_feed
            items, _ = _load_feed()

        ids = [item["id"] for item in items]
        assert ids[0] == "flickr-future"   # year_month "2023-08"
        assert ids[1] == "youtube-mid"     # year_month "2022-01"
        assert ids[2] == "flickr-old"      # year_month "2020-06"
