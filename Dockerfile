# FROM python:3.6.4-alpine3.7
FROM python:3.8.3-alpine3.11

MAINTAINER Soren A D <sorend@gmail.com>

ADD requirements.txt /requirements.txt

RUN apk add --no-cache ca-certificates tini git curl && \
	pip3 install -r /requirements.txt && \
	addgroup -g 1000 www-data && \
	adduser -D -u 1000 -G www-data www-data && \
	mkdir /data && chown www-data /data

ADD ./app /app

WORKDIR /app

USER www-data

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python3", "/app/main.py"]
