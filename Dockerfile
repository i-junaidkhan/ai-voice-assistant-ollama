FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for audio (optional – API mode doesn't need mic)
RUN apt-get update && apt-get install -y portaudio19-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose API port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]