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

# Version injected at Docker build time; changes on every deployment.
APP_VERSION = os.environ.get("APP_VERSION", "dev")

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)
# Make version available to all templates (used for static asset cache-busting).
_jinja_env.globals["app_version"] = APP_VERSION


def render(template_name, **ctx):
    """Render a Jinja2 template and return HTML string."""
    return _jinja_env.get_template(template_name).render(**ctx)


def _feed_etag():
    """Return an ETag token that changes on new deploy OR when the feed updates."""
    if os.path.exists(FEED_FILE):
        mtime = int(os.path.getmtime(FEED_FILE))
        return f"{APP_VERSION}-{mtime}"
    return f"{APP_VERSION}-empty"


def _apply_etag(etag_value, cache_control="no-cache"):
    """Set ETag/Cache-Control response headers.

    If the client already holds the current version (If-None-Match matches),
    raise a 304 Not Modified so Cloudflare and browsers skip the body.
    """
    full_etag = f'"{etag_value}"'
    response.set_header("Cache-Control", cache_control)
    response.set_header("ETag", full_etag)
    if request.environ.get("HTTP_IF_NONE_MATCH") == full_etag:
        raise bottle.HTTPResponse(
            status=304,
            headers={"Cache-Control": cache_control, "ETag": full_etag},
        )


# ── static assets ──────────────────────────────────────────────────────────────

@app.route("/static/<filepath:path>")
def serve_static(filepath):
    """Serve static files from app/static/.

    Long-lived cache is safe because templates append ?v=<APP_VERSION> to
    every static URL, so a new deployment naturally busts Cloudflare's cache.
    """
    result = static_file(filepath, root=STATIC_DIR)
    result.set_header("Cache-Control", "public, max-age=31536000, immutable")
    return result


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


def _load_feed(page=1, page_size=32):
    """Load, sort and paginate the feed from disk.

    Returns a (items, has_more) tuple where has_more indicates whether
    a subsequent page exists.
    """
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE) as fd:
            feed = json.load(fd)
        feed = list(feed.values())
    else:
        feed = []

    feed = list(reversed(sorted(feed, key=lambda x: (
        compute_year_month(x.get("title_date"), x.get("median_taken_date"), x["updated"]),
        x["updated"],
    ))))

    offset = (page - 1) * page_size
    has_more = (offset + page_size) < len(feed)
    items = feed[offset:offset + page_size]

    for item in items:
        item["type"] = "picture" if item["id"].startswith("flickr-") else "video"
        item["year_month"] = compute_year_month(
            item.get("title_date"), item.get("median_taken_date"), item["updated"]
        )
    return items, has_more


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
    _apply_etag(_feed_etag())
    items, _ = _load_feed()
    return jsonp_response(request, response, {"data": items, "success": True})


# ── frontend routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the main page."""
    _apply_etag(APP_VERSION)
    return render('index.html')


@app.route('/feed.html')
def feed_html():
    """Return an htmx-compatible HTML fragment of feed items."""
    page = int(request.query.get('page', 1))
    _apply_etag(f"{_feed_etag()}-p{page}")
    items, has_more = _load_feed(page=page)
    return render('_feed_items.html', items=items, has_more=has_more, next_page=page + 1)


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
