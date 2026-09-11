FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system rx && adduser --system --ingroup rx rx
COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install ".[postgres,redis]"
COPY docker/api-entrypoint.sh /usr/local/bin/api-entrypoint
RUN chmod +x /usr/local/bin/api-entrypoint && chown -R rx:rx /app
USER rx
EXPOSE 8000
ENTRYPOINT ["api-entrypoint"]
