"""Tests for datasources module - Flickr and YouTube loaders."""

import json
import unittest.mock as mock
import pytest


class TestLoadFlickr:
    """Tests for load_flickr()."""

    PHOTOSETS_RESPONSE = {
        "photosets": {
            "photoset": [
                {
                    "id": "72157699000000001",
                    "primary": "42000000001",
                    "farm": "5",
                    "server": "4900",
                    "secret": "abcdef1234",
                    "date_update": "1609459200",  # 2021-01-01 00:00:00 UTC
                    "title": {"_content": "My Photo Album"},
                },
                {
                    "id": "72157699000000002",
                    "primary": "42000000002",
                    "farm": "6",
                    "server": "5000",
                    "secret": "fedcba5678",
                    "date_update": "1612137600",  # 2021-02-01 00:00:00 UTC
                    "title": {"_content": "Second Album"},
                },
            ]
        }
    }

    # getPhotos response for album 1: 3 photos with known datetaken
    # Sorted: "2021-01-15 ...", "2021-01-20 ...", "2021-01-25 ..."  → median = middle = "2021-01-20 12:00:00"
    PHOTOS_RESPONSE_1 = {
        "photoset": {
            "id": "72157699000000001",
            "photo": [
                {"id": "p1", "datetaken": "2021-01-15 10:00:00", "datetakenunknown": "0"},
                {"id": "p2", "datetaken": "2021-01-20 12:00:00", "datetakenunknown": "0"},
                {"id": "p3", "datetaken": "2021-01-25 14:00:00", "datetakenunknown": "0"},
            ],
            "page": 1,
            "pages": 1,
            "total": 3,
        }
    }

    # getPhotos response for album 2: 1 photo
    PHOTOS_RESPONSE_2 = {
        "photoset": {
            "id": "72157699000000002",
            "photo": [
                {"id": "p4", "datetaken": "2021-02-10 10:00:00", "datetakenunknown": "0"},
            ],
            "page": 1,
            "pages": 1,
            "total": 1,
        }
    }

    def _json_side_effects(self):
        """Return side_effect list for json.load: getList + getPhotos per album."""
        return [self.PHOTOSETS_RESPONSE, self.PHOTOS_RESPONSE_1, self.PHOTOS_RESPONSE_2]

    def test_load_flickr_returns_list(self):
        """load_flickr returns a list of dicts."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_load_flickr_item_structure(self):
        """Each Flickr item has required keys with correct format."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        item = result[0]
        assert set(item.keys()) == {"id", "title", "link", "updated", "thumb", "median_taken_date"}

    def test_load_flickr_id_prefix(self):
        """Flickr items have id prefixed with 'flickr-'."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        for item in result:
            assert item["id"].startswith("flickr-")

    def test_load_flickr_link_format(self):
        """Flickr items have correct Flickr album link."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["link"] == "https://www.flickr.com/photos/sorend/sets/72157699000000001/"
        assert result[1]["link"] == "https://www.flickr.com/photos/sorend/sets/72157699000000002/"

    def test_load_flickr_thumb_format(self):
        """Flickr items have correct thumbnail URL."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["thumb"] == "https://farm5.static.flickr.com/4900/42000000001_abcdef1234_m.jpg"

    def test_load_flickr_title(self):
        """Flickr items have correct title from API response."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["title"] == "My Photo Album"
        assert result[1]["title"] == "Second Album"

    def test_load_flickr_updated_from_timestamp(self):
        """Flickr items convert date_update Unix timestamp to datetime string."""
        from datasources import load_flickr
        import datetime

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        # Should be a parseable datetime string
        updated = result[0]["updated"]
        assert isinstance(updated, str)
        # Parse it back - should not raise
        datetime.datetime.fromisoformat(updated)

    def test_load_flickr_calls_getlist_method(self):
        """load_flickr calls the photosets.getList API method."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                load_flickr()
                # getList is the first call
                first_url = mock_urlopen.call_args_list[0][0][0]
                assert "flickr.photosets.getList" in first_url

    def test_load_flickr_calls_getphotos_for_each_album(self):
        """load_flickr calls photosets.getPhotos once per album."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                load_flickr()

        all_urls = [c[0][0] for c in mock_urlopen.call_args_list]
        getphotos_calls = [u for u in all_urls if "flickr.photosets.getPhotos" in u]
        assert len(getphotos_calls) == 2  # one per album

    def test_load_flickr_getphotos_requests_datetaken(self):
        """getPhotos calls include datetaken in the extras parameter."""
        from datasources import load_flickr

        with mock.patch("json.load", side_effect=self._json_side_effects()):
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                load_flickr()

        all_urls = [c[0][0] for c in mock_urlopen.call_args_list]
        getphotos_urls = [u for u in all_urls if "flickr.photosets.getPhotos" in u]
        for url in getphotos_urls:
            assert "date_taken" in url


class TestLoadFlickrMedianTakenDate:
    """Tests for the median_taken_date field computed by load_flickr()."""

    PHOTOSETS_RESPONSE = {
        "photosets": {
            "photoset": [
                {
                    "id": "72157699000000001",
                    "primary": "42000000001",
                    "farm": "5",
                    "server": "4900",
                    "secret": "abcdef1234",
                    "date_update": "1609459200",
                    "title": {"_content": "My Photo Album"},
                }
            ]
        }
    }

    def _make_photos_response(self, photos, page=1, pages=1):
        return {
            "photoset": {
                "id": "72157699000000001",
                "photo": photos,
                "page": page,
                "pages": pages,
                "total": len(photos),
            }
        }

    def test_median_taken_date_present_in_item(self):
        """Each Flickr item has a 'median_taken_date' key."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([
            {"id": "p1", "datetaken": "2021-06-10 10:00:00", "datetakenunknown": "0"},
        ])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert "median_taken_date" in result[0]

    def test_median_of_odd_count_returns_middle(self):
        """Median of an odd number of dates is the middle element."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([
            {"id": "p1", "datetaken": "2021-01-10 00:00:00", "datetakenunknown": "0"},
            {"id": "p2", "datetaken": "2021-01-20 12:00:00", "datetakenunknown": "0"},
            {"id": "p3", "datetaken": "2021-01-30 00:00:00", "datetakenunknown": "0"},
        ])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["median_taken_date"] == "2021-01-20 12:00:00"

    def test_median_of_even_count_returns_average(self):
        """Median of an even number of dates is the midpoint of the two middle elements."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([
            {"id": "p1", "datetaken": "2021-01-10 00:00:00", "datetakenunknown": "0"},
            {"id": "p2", "datetaken": "2021-01-20 00:00:00", "datetakenunknown": "0"},
        ])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        # Midpoint between 2021-01-10 and 2021-01-20 is 2021-01-15 00:00:00
        assert result[0]["median_taken_date"] == "2021-01-15 00:00:00"

    def test_median_none_when_no_photos(self):
        """median_taken_date is None when the album has no photos."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["median_taken_date"] is None

    def test_median_ignores_unknown_dates(self):
        """Photos with datetakenunknown='1' are excluded from the median."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([
            {"id": "p1", "datetaken": "2021-01-10 00:00:00", "datetakenunknown": "1"},
            {"id": "p2", "datetaken": "2021-06-15 12:00:00", "datetakenunknown": "0"},
            {"id": "p3", "datetaken": "2021-12-31 00:00:00", "datetakenunknown": "1"},
        ])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        # Only p2 has a known date
        assert result[0]["median_taken_date"] == "2021-06-15 12:00:00"

    def test_median_none_when_all_dates_unknown(self):
        """median_taken_date is None when all photos have datetakenunknown='1'."""
        from datasources import load_flickr

        photos_resp = self._make_photos_response([
            {"id": "p1", "datetaken": "2021-01-10 00:00:00", "datetakenunknown": "1"},
            {"id": "p2", "datetaken": "2021-06-15 12:00:00", "datetakenunknown": "1"},
        ])
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, photos_resp]):
            with mock.patch("urllib.request.urlopen"):
                result = load_flickr()

        assert result[0]["median_taken_date"] is None

    def test_median_handles_pagination(self):
        """get_median_taken_date fetches all pages when pages > 1."""
        from datasources import load_flickr

        page1 = {
            "photoset": {
                "id": "72157699000000001",
                "photo": [
                    {"id": "p1", "datetaken": "2021-01-10 00:00:00", "datetakenunknown": "0"},
                    {"id": "p2", "datetaken": "2021-06-01 00:00:00", "datetakenunknown": "0"},
                ],
                "page": 1,
                "pages": 2,
                "total": 3,
            }
        }
        page2 = {
            "photoset": {
                "id": "72157699000000001",
                "photo": [
                    {"id": "p3", "datetaken": "2021-12-25 00:00:00", "datetakenunknown": "0"},
                ],
                "page": 2,
                "pages": 2,
                "total": 3,
            }
        }
        with mock.patch("json.load", side_effect=[self.PHOTOSETS_RESPONSE, page1, page2]):
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                result = load_flickr()

        # All 3 dates collected; median is middle = "2021-06-01 00:00:00"
        assert result[0]["median_taken_date"] == "2021-06-01 00:00:00"

        # Should have made 3 urlopen calls: 1 getList + 2 getPhotos pages
        all_urls = [c[0][0] for c in mock_urlopen.call_args_list]
        getphotos_calls = [u for u in all_urls if "flickr.photosets.getPhotos" in u]
        assert len(getphotos_calls) == 2


class TestLoadYoutube:
    """Tests for load_youtube()."""

    CHANNELS_RESPONSE = {
        "items": [
            {
                "contentDetails": {
                    "relatedPlaylists": {
                        "uploads": "UUtest_uploads_playlist"
                    }
                }
            }
        ]
    }

    PLAYLIST_RESPONSE = {
        "items": [
            {
                "snippet": {
                    "title": "My Test Video",
                    "publishedAt": "2021-06-15T12:00:00Z",
                    "resourceId": {"videoId": "testVideoId1"},
                    "thumbnails": {
                        "medium": {"url": "https://i.ytimg.com/vi/testVideoId1/mqdefault.jpg"}
                    },
                }
            },
            {
                "snippet": {
                    "title": "Another_Video",
                    "publishedAt": "2021-07-20T08:30:00Z",
                    "resourceId": {"videoId": "testVideoId2"},
                    "thumbnails": {
                        "medium": {"url": "https://i.ytimg.com/vi/testVideoId2/mqdefault.jpg"}
                    },
                }
            },
        ]
    }

    def _make_mock_youtube(self):
        """Build a mock youtube client that returns test data."""
        mock_yt = mock.MagicMock()

        # channels().list().execute()
        mock_yt.channels.return_value.list.return_value.execute.return_value = (
            self.CHANNELS_RESPONSE
        )

        # playlistItems().list().execute() - first page, no next page
        mock_pl_request = mock.MagicMock()
        mock_pl_request.execute.return_value = self.PLAYLIST_RESPONSE
        mock_yt.playlistItems.return_value.list.return_value = mock_pl_request
        # list_next returns None (no more pages)
        mock_yt.playlistItems.return_value.list_next.return_value = None

        return mock_yt

    def test_load_youtube_returns_list(self):
        """load_youtube returns a list of dicts."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_load_youtube_item_structure(self):
        """Each YouTube item has required keys (no median_taken_date)."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        item = result[0]
        assert set(item.keys()) == {"id", "title", "link", "updated", "thumb"}

    def test_load_youtube_id_prefix(self):
        """YouTube items have id prefixed with 'youtube-'."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        for item in result:
            assert item["id"].startswith("youtube-")

    def test_load_youtube_link_format(self):
        """YouTube items use youtu.be short link format."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        assert result[0]["link"] == "https://youtu.be/testVideoId1"
        assert result[1]["link"] == "https://youtu.be/testVideoId2"

    def test_load_youtube_title_underscore_replaced(self):
        """YouTube titles have underscores replaced with spaces."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        # "Another_Video" -> "Another Video"
        titles = [item["title"] for item in result]
        assert "Another Video" in titles
        assert "Another_Video" not in titles

    def test_load_youtube_updated_format(self):
        """YouTube items have updated formatted as YYYY-MM-DD HH:MM:SS."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        assert result[0]["updated"] == "2021-06-15 12:00:00"

    def test_load_youtube_thumbnail(self):
        """YouTube items use medium thumbnail URL."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()
        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        assert result[0]["thumb"] == "https://i.ytimg.com/vi/testVideoId1/mqdefault.jpg"

    def test_load_youtube_paginates(self):
        """load_youtube follows pagination until list_next returns None."""
        from datasources import load_youtube

        mock_yt = self._make_mock_youtube()

        page2_response = {
            "items": [
                {
                    "snippet": {
                        "title": "Page Two Video",
                        "publishedAt": "2021-08-01T00:00:00Z",
                        "resourceId": {"videoId": "testVideoId3"},
                        "thumbnails": {
                            "medium": {"url": "https://i.ytimg.com/vi/testVideoId3/mqdefault.jpg"}
                        },
                    }
                }
            ]
        }

        page2_request = mock.MagicMock()
        page2_request.execute.return_value = page2_response

        # First call returns page2_request, second returns None
        mock_yt.playlistItems.return_value.list_next.side_effect = [page2_request, None]

        with mock.patch("datasources.build", return_value=mock_yt):
            result = load_youtube()

        assert len(result) == 3
        ids = [item["id"] for item in result]
        assert "youtube-testVideoId3" in ids


class TestLoaders:
    """Tests for the loaders tuple."""

    def test_loaders_contains_flickr_and_youtube(self):
        """loaders tuple contains load_flickr and load_youtube."""
        from datasources import loaders, load_flickr, load_youtube

        assert load_flickr in loaders
        assert load_youtube in loaders
        assert len(loaders) == 2
