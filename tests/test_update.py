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
    },
    {
        "id": "flickr-72157699000000002",
        "title": "Second.Album",
        "link": "https://www.flickr.com/photos/sorend/sets/72157699000000002/",
        "updated": "2021-02-01 00:00:00",
        "thumb": "https://farm6.static.flickr.com/5000/42000000002_fedcba5678_m.jpg",
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
