# Voice Pipeline Hardware Requirements

## Recommended Configurations
- **GPU-Accelerated (preferred)**
  - NVIDIA RTX 4090 (24 GB VRAM) or A6000 class accelerator.
  - CUDA 12.1 drivers with cuDNN 9.x installed on the host.
  - Provision 16 vCPU / 64 GB RAM for concurrency headroom.
  - Set `VOICE_DEVICE_PREFERENCE=cuda` to force GPU execution.
- **CPU-Only Fallback**
  - Dual-socket Intel Xeon or AMD EPYC with AVX2 support.
  - Minimum 16 vCPU / 32 GB RAM.
  - Leave `VOICE_DEVICE_PREFERENCE=auto` (default) to allow automatic CPU selection.

## Storage & Caching
- Whisper and Coqui models are cached under `/models` (Docker volume `voice_models`).
- Session artefacts persist under `/data/voice/sessions`.
- Ensure the `voice_models` volume is backed by fast SSD storage when running in GPU mode.

## Runtime Flags
- `VOICE_SESSIONS_DIR` — directory for persisted transcripts/audio (default `/data/voice/sessions`).
- `VOICE_CACHE_DIR` — model cache root (default `/models`).
- `VOICE_WHISPER_MODEL` — change to `small.en` or `large-v3` to trade accuracy vs. throughput.
- `VOICE_TTS_MODEL` — Coqui model identifier (defaults to `tts_models/en/vctk/vits`).
- `VOICE_SENTIMENT_MODEL` — Hugging Face sentiment pipeline (defaults to `distilbert-base-uncased-finetuned-sst-2-english`).

## Throughput Expectations
- GPU mode: ~180 ms transcription latency for 5-second clips; ~220 ms synthesis latency at 22050 Hz.
- CPU mode: ~950 ms transcription latency for 5-second clips; ~420 ms synthesis latency.
- Sentiment analysis completes in <30 ms on GPU and <80 ms on CPU.

## Monitoring
- Enable FastAPI access logs to track `/voice/sessions` lifecycle.
- Add audio-processing telemetry by watching `app.services.voice.service` logs for pacing metadata.
