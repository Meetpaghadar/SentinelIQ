FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SENTINELIQ_HOST=0.0.0.0
ENV SENTINELIQ_PORT=8000

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sentineliq", "serve"]
