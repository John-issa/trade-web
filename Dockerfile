FROM python:3.11-slim

# tiny init for PID 1
RUN apt-get update && apt-get install -y --no-install-recommends tini && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Copy wrapper
COPY app/ app/
COPY requirements-wrapper.txt ./
COPY docker/prestart.sh /usr/local/bin/prestart.sh
RUN chmod +x /usr/local/bin/prestart.sh

# Install deps (pin exact versions + hashes)
RUN pip install --no-cache-dir -r requirements-wrapper.txt

# Non-root user
RUN useradd -m -u 10001 appuser && \
    mkdir -p /data /tmp && chown -R appuser:appuser /data /tmp /app
USER appuser

ENV REPO_DIR=/app/trade
ENV PORT=8000

# tini -> prestart (git pull) -> gunicorn(uvicorn)
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/usr/local/bin/prestart.sh"]
