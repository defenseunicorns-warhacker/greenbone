FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY . .

EXPOSE 80

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
