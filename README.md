# Whisper Streaming for Wowza Streaming Engine

Current release: 1.3.0 (Phase 3 completion – source-stream removal & image slimming). See `CHANGELOG.md` for details.

Dockerized low-latency Whisper transcription service for integration with the Wowza Streaming Engine module [wse-plugin-caption-handlers](https://github.com/WowzaMediaSystems/wse-plugin-caption-handlers).

The server exposes a single TCP port (3000) and expects raw 16 kHz mono PCM16LE audio bytes. It outputs newline‑delimited JSON objects (schema frozen) representing partial / committed transcript segments.

## Usage

### Repository Files (Selected)

| File / Script                     | Purpose                                                                    |
| --------------------------------- | -------------------------------------------------------------------------- |
| `Dockerfile`                      | Build image (python:3.12-slim + minimal deps)                              |
| `docker-compose.yaml`             | Example stack with Wowza + this service                                    |
| `local_build.ps1`                 | Convenience PowerShell build script (tags image `whisper_streaming:local`) |
| `local_run.ps1`                   | PowerShell run helper (sets env vars, publishes port)                      |
| `whisper_online_server.py`        | TCP server entrypoint (raw PCM in, JSON out)                               |
| `.github/copilot-instructions.md` | Guardrails for AI assistants                                               |

### Environment Variables

| Variable       |        Default | Description                                                                                                                                              |
| :------------- | -------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BACKEND        | faster-whisper | [faster-whisper,openai-api] Backend to use (local faster-whisper or OpenAI API).                                                                         |
| MODEL          |        tiny.en | Whisper model size (tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo). Auto-downloaded to /tmp. |
| USE_GPU        |          False | Use the GPU if available (only meaningful for faster-whisper).                                                                                           |
| LANGUAGE       |           auto | Source language code, or 'auto' for detection.                                                                                                           |
| LOG_LEVEL      |           INFO | [DEBUG,INFO,WARNING,ERROR,CRITICAL] Logging level.                                                                                                       |
| MIN_CHUNK_SIZE |              1 | Minimum audio chunk size (seconds) before processing.                                                                                                    |
| SAMPLING_RATE  |          16000 | Input sample rate (must match bytes sent).                                                                                                               |

### Output JSON Format

Each line emitted by the server stdout is one JSON object (ordering & fields are immutable):

```json
{
  "language": "en",
  "start": "7.580",
  "end": "8.540",
  "text": "this is text from whisper"
}
```

Do not rely on spacing (keys may appear without extra whitespace). Field order: `language`, `start`, `end`, `text`.

### Quick Test (One-Liner)

```
ffmpeg -hide_banner -loglevel error -re -i <video_file.mp4> -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

Expect streaming JSON lines in the server logs.

---

## Manual Test Guide (Windows)

### Prerequisites

- Windows 10/11 + PowerShell
- Python 3.12+ (3.13 supported)
- `ffmpeg` in PATH
- `ncat` (Nmap) in PATH (`choco install nmap -y` or install from site)
- (Optional) Sample speech MP3 at `./samples/audio.mp3`

### 1. Virtual Environment

```
python -m venv .venv
./.venv/Scripts/Activate.ps1
```

If scripts blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 2. Install Dependencies

```
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run Server (CPU tiny model example)

```
python .\whisper_online_server.py --language no --model tiny
```

Server listens on `0.0.0.0:3000`.

### 4. Stream Audio

```
ffmpeg -hide_banner -loglevel error -re -i .\samples\audio.mp3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

### 5. Observe Output

JSON lines like:

```
{"language": "no", "start": "7.580", "end": "8.540", "text": "<partial transcript>"}
```

### 6. Tone Smoke Test

```
ffmpeg -f lavfi -i sine=frequency=440:sample_rate=16000 -t 3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

### 7. Stop

Ctrl+C (graceful shutdown improvements planned in Phase 4).

### Troubleshooting

| Symptom              | Cause                | Fix                                            |
| -------------------- | -------------------- | ---------------------------------------------- |
| `ncat` not found     | PATH missing         | Ensure Nmap install dir in PATH / reopen shell |
| `ffmpeg` not found   | Not installed        | Install + reopen PowerShell                    |
| Immediate disconnect | Wrong host/port      | Confirm server log shows Listening on 3000     |
| No JSON output       | Silence / non-speech | Use clearer speech sample                      |
| High latency         | Large model on CPU   | Use `tiny` or GPU (`--use_gpu True`)           |

### Validation Checklist

- Server starts (no import errors)
- Receives raw PCM and stays running
- Emits JSON lines with all four fields
- Stops cleanly with Ctrl+C

---

## GPU

GPU acceleration (optional) – minimal baseline image currently CPU-oriented. To enable GPU you will need to extend the Dockerfile (adding `torch`/`triton` + CUDA libs) and run container with `--gpus all` plus `USE_GPU=True`. (No official GPU Dockerfile included yet.)

## Acknowledgments

Based on:

- [Whisper Streaming](https://github.com/ufal/whisper_streaming)
- [OpenAI Whisper](https://github.com/openai/whisper)
- Original Wowza integration README

---

Documentation consolidated (`TEST.md` merged here). JSON schema and trimming semantics are frozen.
