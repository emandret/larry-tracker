FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY src ./src
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "location_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
