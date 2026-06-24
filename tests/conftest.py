"""Shared pytest fixtures and configuration."""

import os
import sys

# Ensure required env vars are set BEFORE any app modules are imported
# (datasources.py and main.py read them at module level)
os.environ.setdefault("FLICKR_API_KEY", "test_flickr_key")
os.environ.setdefault("FLICKR_USERID", "test_flickr_user")
os.environ.setdefault("YOUTUBE_DEVELOPER_KEY", "test_yt_key")
os.environ.setdefault("YOUTUBE_CHANNEL", "test_yt_channel")
os.environ.setdefault("FEED_FILE", "/tmp/test_feed.json")

# Ensure app/ is on the path for imports
APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
