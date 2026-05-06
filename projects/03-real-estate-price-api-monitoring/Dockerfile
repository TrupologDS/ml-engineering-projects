FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    MAIN_APP_PORT=1702 \
    MODEL_PATH=services/models/model.pkl \
    LOG_LEVEL=INFO

WORKDIR /app

COPY services/requirements.txt ./services/requirements.txt
RUN pip install --no-cache-dir -r services/requirements.txt


COPY services ./services

EXPOSE 1702

CMD ["sh", "-c", "uvicorn services.ml_service.price_app:app --host 0.0.0.0 --port ${MAIN_APP_PORT}"]
