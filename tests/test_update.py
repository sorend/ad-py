"""Tests for update module - feed cache update logic."""

import json
import os
import unittest.mock as mock
import pytest


SAMPLE_FLICKR_ITEMS = [
    {
        "id": "flickr-72157699000000001",
        "title": "My Photo Album",
        "link": "https://www.flickr.com/photos/sorend/sets/72157699000000001/",
        "updated": "2021-01-01 00:00:00",
        "thumb": "https://farm5.static.flickr.com/4900/42000000001_abcdef1234_m.jpg",
        "median_taken_date": "2021-01-15 12:00:00",
    },
    {
        "id": "flickr-72157699000000002",
        "title": "Second.Album",
        "link": "https://www.flickr.com/photos/sorend/sets/72157699000000002/",
        "updated": "2021-02-01 00:00:00",
        "thumb": "https://farm6.static.flickr.com/5000/42000000002_fedcba5678_m.jpg",
        "median_taken_date": None,
    },
]

SAMPLE_YOUTUBE_ITEMS = [
    {
        "id": "youtube-testVideoId1",
        "title": "My Test Video",
        "link": "https://youtu.be/testVideoId1",
        "updated": "2021-06-15 12:00:00",
        "thumb": "https://i.ytimg.com/vi/testVideoId1/mqdefault.jpg",
    },
]


class TestUpdateFeed:
    """Tests for update_feed()."""

    def _patch_loaders(self, flickr_items=None, youtube_items=None):
        """Return a patch for datasources.loaders."""
        flickr_items = flickr_items if flickr_items is not None else SAMPLE_FLICKR_ITEMS
        youtube_items = youtube_items if youtube_items is not None else SAMPLE_YOUTUBE_ITEMS

        mock_flickr = mock.MagicMock(return_value=flickr_items)
        mock_youtube = mock.MagicMock(return_value=youtube_items)
        return mock.patch("update.loaders", (mock_flickr, mock_youtube))

    def test_update_feed_creates_feed_file(self, tmp_path):
        """update_feed writes a feed.json file."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        assert os.path.exists(feed_file)

    def test_update_feed_writes_valid_json(self, tmp_path):
        """update_feed writes valid JSON to the feed file."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert isinstance(data, dict)

    def test_update_feed_contains_all_items(self, tmp_path):
        """update_feed stores all items from all loaders."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert "flickr-72157699000000001" in data
        assert "flickr-72157699000000002" in data
        assert "youtube-testVideoId1" in data

    def test_update_feed_keyed_by_id(self, tmp_path):
        """Feed items are stored as a dict keyed by item id."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        for key, value in data.items():
            assert key == value["id"]

    def test_update_feed_sanitizes_dots_in_title(self, tmp_path):
        """update_feed replaces dots in titles with spaces."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        # "Second.Album" should become "Second Album"
        assert data["flickr-72157699000000002"]["title"] == "Second Album"

    def test_update_feed_sanitizes_underscores_in_title(self, tmp_path):
        """update_feed replaces underscores in titles with spaces."""
        flickr_items = [
            {
                "id": "flickr-111",
                "title": "Under_score_Album",
                "link": "https://flickr.com/1",
                "updated": "2021-01-01 00:00:00",
                "thumb": "https://flickr.com/thumb1.jpg",
            }
        ]
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders(flickr_items=flickr_items, youtube_items=[]):
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert data["flickr-111"]["title"] == "Under score Album"

    def test_update_feed_merges_existing_data(self, tmp_path):
        """update_feed merges new items with existing feed, not overwriting all."""
        feed_file = str(tmp_path / "feed.json")

        # Pre-existing feed with one item
        existing_feed = {
            "flickr-existing-001": {
                "id": "flickr-existing-001",
                "title": "Existing Album",
                "link": "https://flickr.com/existing",
                "updated": "2020-01-01 00:00:00",
                "thumb": "https://flickr.com/existing_thumb.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(existing_feed, f)

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        # Old item should still be present
        assert "flickr-existing-001" in data
        # New items should also be present
        assert "flickr-72157699000000001" in data
        assert "youtube-testVideoId1" in data

    def test_update_feed_upserts_existing_items(self, tmp_path):
        """update_feed updates items that already exist in the feed."""
        feed_file = str(tmp_path / "feed.json")

        # Pre-existing feed with stale version of an item
        existing_feed = {
            "flickr-72157699000000001": {
                "id": "flickr-72157699000000001",
                "title": "Old Title",
                "link": "https://flickr.com/old",
                "updated": "2020-01-01 00:00:00",
                "thumb": "https://flickr.com/old_thumb.jpg",
            }
        }
        with open(feed_file, "w") as f:
            json.dump(existing_feed, f)

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        # Item should be updated to new values
        assert data["flickr-72157699000000001"]["title"] == "My Photo Album"

    def test_update_feed_no_existing_file(self, tmp_path):
        """update_feed works fine when feed.json does not yet exist."""
        feed_file = str(tmp_path / "feed.json")
        assert not os.path.exists(feed_file)

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        assert os.path.exists(feed_file)

    def test_update_feed_output_sorted_keys(self, tmp_path):
        """update_feed writes JSON with sort_keys=True."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            raw = f.read()

        # Re-parse and re-dump with sort_keys to compare
        parsed = json.loads(raw)
        re_serialized = json.dumps(parsed, indent=2, sort_keys=True)
        assert raw == re_serialized

    def test_update_feed_title_date_extracted_before_sanitization(self, tmp_path):
        """title_date is extracted from the raw title before dots are replaced."""
        flickr_items = [
            {
                "id": "flickr-111",
                "title": "2023.05.15 Summer holiday",
                "link": "https://flickr.com/1",
                "updated": "2023-05-15 00:00:00",
                "thumb": "https://flickr.com/thumb1.jpg",
                "median_taken_date": None,
            }
        ]
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders(flickr_items=flickr_items, youtube_items=[]):
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        item = data["flickr-111"]
        # title_date extracted from original "2023.05.15 ..." → "2023-05"
        assert item["title_date"] == "2023-05"
        # title sanitized AFTER extraction: dots → spaces
        assert item["title"] == "2023 05 15 Summer holiday"

    def test_update_feed_title_date_none_when_no_date_in_title(self, tmp_path):
        """title_date is None when the title contains no recognisable date."""
        flickr_items = [
            {
                "id": "flickr-222",
                "title": "My Plain Album",
                "link": "https://flickr.com/2",
                "updated": "2021-01-01 00:00:00",
                "thumb": "https://flickr.com/thumb2.jpg",
                "median_taken_date": None,
            }
        ]
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders(flickr_items=flickr_items, youtube_items=[]):
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert data["flickr-222"]["title_date"] is None

    def test_update_feed_title_date_with_danish_month(self, tmp_path):
        """title_date is extracted correctly for titles with Danish month names."""
        flickr_items = [
            {
                "id": "flickr-333",
                "title": "2022 Juni ferie",
                "link": "https://flickr.com/3",
                "updated": "2022-06-01 00:00:00",
                "thumb": "https://flickr.com/thumb3.jpg",
                "median_taken_date": None,
            }
        ]
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders(flickr_items=flickr_items, youtube_items=[]):
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert data["flickr-333"]["title_date"] == "2022-06"

    def test_update_feed_title_date_stored_in_feed_file(self, tmp_path):
        """title_date is present in every item written to the feed file."""
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders():
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        for item in data.values():
            assert "title_date" in item

    def test_update_feed_youtube_title_date_extracted(self, tmp_path):
        """title_date is also extracted for YouTube items."""
        youtube_items = [
            {
                "id": "youtube-abc",
                "title": "2021 July vlog",
                "link": "https://youtu.be/abc",
                "updated": "2021-07-10 00:00:00",
                "thumb": "https://i.ytimg.com/vi/abc/mqdefault.jpg",
            }
        ]
        feed_file = str(tmp_path / "feed.json")

        with mock.patch("update.FEED_FILE", feed_file):
            with self._patch_loaders(flickr_items=[], youtube_items=youtube_items):
                from update import update_feed
                update_feed()

        with open(feed_file) as f:
            data = json.load(f)

        assert data["youtube-abc"]["title_date"] == "2021-07"
