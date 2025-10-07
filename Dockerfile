FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential rsync && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-wrapper.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Writable, persisted
RUN mkdir -p /data/captures /srv/trade-repo

ENV REPO_DIR=/srv/trade-repo \
    OUTPUT_DIR=/data/captures \
    REPO_GIT=https://github.com/slsecret/options-trading-assistant \
    MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
