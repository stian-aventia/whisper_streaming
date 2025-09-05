# Whisper Streaming for Wowza Streaming Engine

Current release: 1.6.0 (recv loop sentinels, socket timeout, auto GPU & bundled CUDA runtime). See `CHANGELOG.md` for details.

Dockerized low-latency Whisper transcription service for integration with the Wowza Streaming Engine module [wse-plugin-caption-handlers](https://github.com/WowzaMediaSystems/wse-plugin-caption-handlers).

The server exposes a single TCP port (3000) and expects raw 16 kHz mono PCM16LE audio bytes. It outputs newline‑delimited JSON objects (schema frozen) representing partial / committed transcript segments.

## Usage

### Local GPU (Windows) Prerequisites (faster-whisper)

GPU is auto-detected (no env var needed). If CUDA toolchain + cuDNN (now baked into the default Docker image) are available (ctranslate2.get_cuda_device_count()>0) it uses GPU; use `--disable_gpu` to force CPU.

If you want GPU acceleration locally on Windows (backend `faster-whisper`), install BOTH:

1. NVIDIA CUDA Toolkit 12.x (includes drivers if needed)

- Download: https://developer.nvidia.com/cuda-downloads
- Reopen PowerShell after install so PATH updates apply.

2. cuDNN 9 for Windows (separate installer – not bundled in CUDA Toolkit)

- Download: https://developer.nvidia.com/cudnn (choose Windows x86_64, matching CUDA 12)
- Run installer (no manual DLL copy required in recent versions). Reboot if DLL errors persist.

3. Torch is NOT required for faster-whisper GPU support; ctranslate2 uses CUDA directly.
4. Verify:

```powershell
python -c "import ctranslate2; print('CUDA available:', ctranslate2.get_cuda_device_count())"
```

Expect `CUDA available: 1`. If you see `Could not locate cudnn_ops64_9.dll`, (re)install cuDNN or reboot.

Docker image (default `Dockerfile`) includes required CUDA 12 runtime libs (cudart, cublas, cuDNN) for faster-whisper; host driver still required. Run container with `--gpus all` for GPU, omit for CPU. `USE_GPU` env deprecated (auto-detect).

---

### Docker Quick Start

Build image (CPU baseline):

```powershell
docker build -t whisper_streaming:local .
```

Run tiny model on port 3000 (CPU or auto GPU if available):

```powershell
docker run -e MODEL=tiny -p 3000:3000 -t whisper_streaming:local
```

Optional GPU (adds GPU devices; app auto-detects):

```powershell
docker run --gpus all -e MODEL=tiny -p 3000:3000 -t whisper_streaming:local
```

Pipe audio for a quick test (replace input as needed):

```powershell
ffmpeg -hide_banner -loglevel error -re -i .\samples\audio_king.mp3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

Each JSON line appears in container logs (stdout).

---

### Repository Files (Selected)

| File / Script                     | Purpose                                                       |
| --------------------------------- | ------------------------------------------------------------- |
| `Dockerfile`                      | Build image (python:3.12-slim + CUDA 12 runtime libs + cuDNN) |
| `docker_build.ps1`                | Minimal build helper (tags image whisper_streaming:local)     |
| `docker_run.ps1`                  | Minimal run helper (adds --gpus all by default)               |
| `docker-compose.yaml`             | Example stack with Wowza + this service                       |
| `local_build.ps1`                 | (Local convenience) Build image tag `whisper_streaming:local` |
| `local_run.ps1`                   | (Local convenience) Run tiny model container locally          |
| `whisper_online_server.py`        | TCP server entrypoint (raw PCM in, JSON out)                  |
| `.github/copilot-instructions.md` | Guardrails for AI assistants                                  |

### Environment Variables

| Variable             |        Default | Description                                                                                                                                            |
| :------------------- | -------------: | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| BACKEND              | faster-whisper | [faster-whisper,openai-api] Backend to use (local faster-whisper or OpenAI API).                                                                       |
| MODEL                |        tiny.en | Model identifier: builtin size (tiny…large-\*), local path, or HuggingFace repo id (e.g. NbAiLab/nb-whisper-large). Auto-downloaded to /tmp if remote. |
| (deprecated) USE_GPU |          (n/a) | Ignored (auto-detect). Remove from deployments.                                                                                                        |
| DISABLE_GPU          |         (flag) | CLI flag `--disable_gpu` (or env `DISABLE_GPU=1`) forces CPU even if CUDA present.                                                                     |
| LANGUAGE             |           auto | Source language code, or 'auto' for detection.                                                                                                         |
| LOG_LEVEL            |           INFO | [DEBUG,INFO,WARNING,ERROR,CRITICAL] Logging level.                                                                                                     |
| MIN_CHUNK_SIZE       |              1 | Minimum audio chunk size (seconds) before processing.                                                                                                  |
| SAMPLING_RATE        |          16000 | Input sample rate (must match bytes sent).                                                                                                             |

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
| High latency         | Large model on CPU   | Use `tiny` (auto GPU if available)             |

### Validation Checklist

- Server starts (no import errors)
- Receives raw PCM and stays running
- Emits JSON lines with all four fields
- Stops cleanly with Ctrl+C

---

## GPU

GPU acceleration (optional) – baseline image is CPU-oriented. If CUDA is available inside container/host, GPU is used automatically. Force CPU: `--disable_gpu`. For containers add `--gpus all`.

## Acknowledgments

Based on:

- [Whisper Streaming](https://github.com/ufal/whisper_streaming)
- [OpenAI Whisper](https://github.com/openai/whisper)
- Original Wowza integration README

---

Documentation consolidated (`TEST.md` merged here). JSON schema and trimming semantics are frozen.
