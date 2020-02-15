#!/usr/bin/env python3

from datasources import loaders
import json
import os

from main import FEED_FILE

def update_feed():
    feed = {}
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, "r") as fd:
            feed = json.load(fd)

    old = len(feed)
    
    for loader in loaders:
        current = loader()
        for item in current:
            item["title"] = item["title"].replace(".", " ").replace("_", " ")
            feed[item["id"]] = item

    with open(FEED_FILE, "w") as fd:
        json.dump(feed, fd, indent=2, sort_keys=True)

    print("updated feed, old items", old, "new items", len(feed))
