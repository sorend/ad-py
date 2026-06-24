#!/usr/bin/env python3
"""Main entry for Bottle application."""

import json
import logging
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from healthcheck import HealthCheck, EnvironmentDump
import bottle
from bottle import request, response, static_file
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dates import compute_year_month

app = application = bottle.Bottle()

health = HealthCheck()
envdump = EnvironmentDump()

# Paths relative to this file so they work regardless of working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_HERE, "static")
TEMPLATE_DIR = os.path.join(_HERE, "templates")

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)


def render(template_name, **ctx):
    """Render a Jinja2 template and return HTML string."""
    return _jinja_env.get_template(template_name).render(**ctx)


# ── static assets ──────────────────────────────────────────────────────────────

@app.route("/static/<filepath:path>")
def serve_static(filepath):
    """Serve static files from app/static/."""
    return static_file(filepath, root=STATIC_DIR)


# ── health / environment ───────────────────────────────────────────────────────

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


# ── feed data ──────────────────────────────────────────────────────────────────

FEED_FILE = os.environ['FEED_FILE']
print("- Using feed file", FEED_FILE)


def _load_feed(limit=32):
    """Load, sort and truncate the feed from disk."""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE) as fd:
            feed = json.load(fd)
        feed = list(feed.values())
    else:
        feed = []

    feed = list(reversed(sorted(feed, key=lambda x: (
        compute_year_month(x.get("title_date"), x.get("median_taken_date"), x["updated"]),
        x["updated"],
    ))))[:limit]
    for item in feed:
        item["type"] = "picture" if item["id"].startswith("flickr-") else "video"
        item["year_month"] = compute_year_month(
            item.get("title_date"), item.get("median_taken_date"), item["updated"]
        )
    return feed


def jsonp_response(request, response, dictionary):
    """Produce jsonp response."""
    if request.query.callback:
        response.content_type = "application/javascript"
        return "%s(%s);" % (request.query.callback, json.dumps(dictionary))
    return dictionary


@app.route('/feed.r')
def feed_reset():
    """Remove the feed cache."""
    if os.path.exists(FEED_FILE):
        os.remove(FEED_FILE)


@app.route('/feed.x')
def feed():
    """Retrieve the feed as JSON (or JSONP when ?callback= is given)."""
    sfeed = _load_feed()
    return jsonp_response(request, response, {"data": sfeed, "success": True})


# ── frontend routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the main page."""
    return render('index.html')


@app.route('/feed.html')
def feed_html():
    """Return an htmx-compatible HTML fragment of feed items."""
    return render('_feed_items.html', items=_load_feed())


@app.error(404)
def error404(error):
    """Custom 404 page."""
    return render('notfound.html')


# ── scheduler ─────────────────────────────────────────────────────────────────

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _start_scheduler()
    # Only fetch on startup when there is no cached feed yet.
    # Set FORCE_UPDATE=1 to override and always refresh on start.
    if not os.path.exists(FEED_FILE) or os.environ.get("FORCE_UPDATE"):
        from update import update_feed
        update_feed()
    else:
        logging.info("Feed cache found at %s, skipping initial update", FEED_FILE)
    from waitress import serve
    serve(app, listen="*:8080")
