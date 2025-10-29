FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV FASTER_WHISPER_CACHE=/models/whisper \
    COQUI_TTS_CACHE=/models/tts

RUN mkdir -p "$FASTER_WHISPER_CACHE" "$COQUI_TTS_CACHE"

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

