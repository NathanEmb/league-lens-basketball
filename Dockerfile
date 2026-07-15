FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt-get -y update; apt-get -y install curl

WORKDIR /app

ADD . /app

ENV PYTHONPATH=.

RUN uv sync --frozen 

ENV PORT=8000

CMD uv run uvicorn src.app:app --host 0.0.0.0 --port $PORT