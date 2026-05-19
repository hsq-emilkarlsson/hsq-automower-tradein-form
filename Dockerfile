FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
COPY vendor vendor/
RUN pip install --no-cache-dir --no-index --find-links vendor -r requirements.txt

COPY . .

# Run as root so the pod can write to the DevPlatform-provisioned PVC.
# The PVC mount point is root-owned; only root (or fsGroup config) can
# initialise it. DevPlatform SCC for this namespace allows root (evidenced
# by pod 215359 which ran as root and successfully wrote to the same PVC).
USER root

RUN mkdir -p data uploads && \
    chmod -R g+rwX data uploads

# Port 4001 required by Husqvarna DevPlatform
EXPOSE 4001

# Platform requires /healthz with specific JSON (BUILD_ID, SOURCE_VERSION, etc.)
HEALTHCHECK CMD curl --fail http://localhost:4001/healthz || exit 1

# Startup script: fix PVC mount permissions at runtime (OpenShift mounts the PVC
# after image layers are applied, overwriting the chown/chmod above). chmod may
# fail silently if we are not the file owner, but if the previous pod (which ran
# as root) already set g+rwX the non-root pod with supplemental group 0 can write.
RUN printf '#!/bin/sh\nmkdir -p /app/data /app/uploads\nchmod -R g+rwX /app/data /app/uploads 2>/dev/null || true\nexec uvicorn backend.app:app --host 0.0.0.0 --port 4001\n' \
    > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
