FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /square

COPY . .

RUN uv sync --locked --no-dev

CMD ["uv", "run", "main.py"]