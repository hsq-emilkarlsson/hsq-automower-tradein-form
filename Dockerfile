FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data uploads

ENV DB_PATH=/app/data/tradein.db
ENV UPLOADS_DIR=/app/uploads

# Port 4001 required by Husqvarna DevPlatform
EXPOSE 4001

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "4001"]

