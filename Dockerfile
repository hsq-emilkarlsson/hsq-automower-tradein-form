FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
COPY vendor vendor/
RUN pip install --no-cache-dir --no-index --find-links vendor -r requirements.txt

COPY . .

RUN mkdir -p data uploads && \
    chown -R 1000:0 data uploads && \
    chmod -R g+rwX data uploads

# Port 4001 required by Husqvarna DevPlatform
EXPOSE 4001

# Platform requires /healthz with specific JSON (BUILD_ID, SOURCE_VERSION, etc.)
HEALTHCHECK CMD curl --fail http://localhost:4001/healthz || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "4001"]
