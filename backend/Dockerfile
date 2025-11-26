FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Create a Python virtual environment and activate it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /src/backend/requirements.txt
RUN pip install uv
ENV UV_HTTP_TIMEOUT=1200
RUN uv pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install -r /src/backend/requirements.txt

ENV FASTER_WHISPER_CACHE=/models/whisper \
    COQUI_TTS_CACHE=/models/tts

RUN mkdir -p "$FASTER_WHISPER_CACHE" "$COQUI_TTS_CACHE"

COPY . /src/backend
ENV PYTHONPATH=/src

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

