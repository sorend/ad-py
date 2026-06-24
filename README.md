
# ad-py

Python backend for atmakuridavidsen.com website — aggregates Flickr photo albums and YouTube videos into a single feed API.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
make install   # install dependencies
make test      # run tests
make run       # run locally (requires env vars below)
```

Required environment variables:

| Variable | Description |
|---|---|
| `FLICKR_API_KEY` | Flickr API key |
| `FLICKR_USERID` | Flickr user ID |
| `YOUTUBE_DEVELOPER_KEY` | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL` | YouTube channel ID |

## Docker

```bash
make docker-build   # build image locally
make docker-run     # run container (passes env vars from shell)
```

## API

| Endpoint | Description |
|---|---|
| `GET /feed.x` | Returns the 32 most-recently-updated feed items (JSON or JSONP via `?callback=`) |
| `GET /feed.r` | Invalidates the feed cache |
| `GET /healthz` | Health check |
| `GET /environment.x` | Runtime environment dump |
