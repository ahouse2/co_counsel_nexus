FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# Install Python 3.11 and other necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a Python virtual environment and activate it
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/requirements.txt
RUN pip install uv
ENV UV_HTTP_TIMEOUT=1200
RUN uv pip install -r requirements.txt --prerelease=allow

ENV FASTER_WHISPER_CACHE=/models/whisper \
    COQUI_TTS_CACHE=/models/tts

RUN mkdir -p "$FASTER_WHISPER_CACHE" "$COQUI_TTS_CACHE"

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

