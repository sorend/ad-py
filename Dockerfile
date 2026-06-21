FROM python:3.12-alpine3.21

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apk add --no-cache ca-certificates tini git curl && \
    adduser -D -u 1000 -G www-data www-data && \
    mkdir /data && chown www-data /data

COPY pyproject.toml uv.lock /app/

WORKDIR /app

RUN uv sync --no-dev --no-install-project && \
    rm -rf /root/.cache

COPY ./app /app

USER www-data

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["uv", "run", "--no-dev", "python", "/app/main.py"]
