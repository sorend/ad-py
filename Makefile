.PHONY: install test lint run docker-build docker-run clean

# Install all dependencies including dev
install:
	uv sync --extra dev

# Run tests
test:
	uv run pytest tests/ -v

# Run linter
lint:
	uv run ruff check app/ tests/

# Run the application locally (requires env vars)
run:
	uv run python app/main.py

# Build Docker image
docker-build:
	docker build -t ad-py:local .

# Run Docker container locally (requires env vars)
docker-run: docker-build
	docker run --rm \
	  -e FLICKR_API_KEY \
	  -e FLICKR_USERID \
	  -e YOUTUBE_DEVELOPER_KEY \
	  -e YOUTUBE_CHANNEL \
	  -p 8080:8080 \
	  ad-py:local

# Remove build artifacts and venv
clean:
	rm -rf .venv dist *.egg-info __pycache__ app/__pycache__ tests/__pycache__
