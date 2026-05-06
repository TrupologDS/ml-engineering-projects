FROM python:3.10-slim

WORKDIR /app

# Service dependencies only
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Code and artifacts
COPY services/recommendation_service.py ./services/recommendation_service.py
COPY models ./models

EXPOSE 8000
CMD ["uvicorn", "services.recommendation_service:app", "--host", "0.0.0.0", "--port", "8000"]
