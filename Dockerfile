FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_HTTP_TIMEOUT=120

WORKDIR /app

RUN pip install --upgrade pip uv

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --no-install-project

COPY src ./src
COPY eval ./eval
COPY apps ./apps
COPY scripts ./scripts
COPY main.py ./
COPY README.md ./

EXPOSE 8000

CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
