#!/usr/bin/env python3
"""Main entry for Bottle application."""

import json
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from healthcheck import HealthCheck, EnvironmentDump
import bottle
from bottle import request, response

app = application = bottle.Bottle()

health = HealthCheck()
envdump = EnvironmentDump()


@app.route("/healthz")
def healthcheck():
    """Health check."""
    message, status, headers = health.run()
    return bottle.HTTPResponse(body=message, status=status, headers=headers)


@app.route("/environment.x")
def environmentdump():
    """Environment exposer."""
    message, status, headers = envdump.run()
    return bottle.HTTPResponse(body=message, status=status, headers=headers)


FEED_FILE = "/data/feed.json"
# FEED_FILE = os.path.join(os.path.dirname(__file__), "feed.json")
print("- Using feed file", FEED_FILE)


def jsonp(request, response, dictionary):
    """Produce jsonp response."""
    if (request.query.callback):
        response.content_type = "application/javascript"
        return "%s(%s);" % (request.query.callback, json.dumps(dictionary))
    else:
        return dictionary


@app.route('/feed.r')
def feed_reset():
    """Remove the feed cache."""
    if os.path.exists(FEED_FILE):
        os.remove(FEED_FILE)


@app.route('/feed.x')
def feed():
    """Retrieve the feed cache."""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE) as fd:
            feed = json.load(fd)
        feed = feed.values()
    else:
        feed = []

    # sort and take 10 newest entries
    sfeed = list(reversed(sorted(feed, key=lambda x: x["updated"])))
    sfeed = sfeed[:32]
    for x in sfeed:
        x["type"] = "picture" if x["id"].startswith("flickr-") else "video"

    return jsonp(request, response, {"data": sfeed, "success": True})


def _start_scheduler():
    from update import update_feed
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        func=update_feed,
        trigger=IntervalTrigger(minutes=30),
        id='update-job',
        name='Update feed.json',
        replace_existing=True)
    atexit.register(lambda: scheduler.shutdown())

    def scheduler_health():
        """Scheduler health check."""
        jobs = len(scheduler.get_jobs())
        if jobs == 1:
            return True, "Scheduler has one job scheduled"
        return False, "Scheduler is empty"
    health.add_check(scheduler_health)


if __name__ == "__main__":
    _start_scheduler()
    from update import update_feed
    update_feed()
    from waitress import serve
    serve(app, listen="*:8080")
