FROM ghcr.io/astral-sh/uv:python3.14-slim

WORKDIR /square

COPY . .

RUN uv sync --locked --no-dev

CMD ["uv", "run", "--frozen", "--no-dev", "main.py"]
