# Manual Test Guide (Windows)

Purpose: Quick manual verification of the streaming server after recent trimming / tokenizer removals. Produces live JSON transcript lines on stdout of the server.

## Prerequisites

- Windows 10/11 with PowerShell.
- Python 3.12+ (3.13 supported).
- ffmpeg in PATH (https://ffmpeg.org/download.html or via winget/choco).
- ncat (from Nmap) in PATH:
  - Option A (installer): Download & install Nmap (https://nmap.org/download.html) – installer adds `ncat.exe` to PATH (or copy `ncat.exe` manually).
  - Option B (Chocolatey):
    ```powershell
    choco install nmap -y
    ```
    Reopen PowerShell so PATH updates; verify with `ncat --version`.
- (Optional) Sample audio file at `./samples/audio_king.mp3` (create `samples` folder if missing). Any speech MP3 works.

## 1. Clone / Open Project

If not already:

```
git clone <repo-url>
cd whisper_streaming
```

## 2. Create & Activate Virtual Environment

PowerShell:

```
python -m venv .venv
./.venv/Scripts/Activate.ps1
```

(If script execution is blocked: run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then activate again.)

## 3. Install Dependencies

```
pip install --upgrade pip
pip install -r requirements.txt
```

Expected: installs `faster-whisper`, `librosa`, `soundfile`, `openai`, etc.

## 4. Start the Streaming Server

```
python .\whisper_online_server.py --language no --model tiny
```

Notes:

- `--model tiny` keeps startup fast.
- `--language no` sets reported language (falls back to 'en' if auto-detected else).
- Server listens on TCP port 3000.

You should see logs ending with something like: `Listening on('0.0.0.0', 3000)`.

## 5. Feed Audio From Another Terminal

Open a second PowerShell (keep server running in first). If venv is needed for ffmpeg PATH, activate it again.

Stream an MP3 file as 16 kHz mono signed 16‑bit little endian raw audio to the server:

```
ffmpeg -hide_banner -loglevel error -re -i .\samples\audio_king.mp3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

Explanation:

- `-re` simulates real-time pacing.
- Audio is transcoded to raw PCM16LE, piped into `ncat` which sends bytes over the TCP connection.

## 6. Observe Output

In the server window you should see INFO log lines plus JSON lines similar to:

```
{"language": "no", "start": "7.580", "end": "8.540", "text": "<partial transcript>"}
```

Multiple lines will appear as streaming continues. (The first few seconds may produce little or no text depending on audio.)

## 7. Optional: Quick Silence / Tone Smoke Test

If you just want to ensure pipeline stability without a file:

```
ffmpeg -f lavfi -i sine=frequency=440:sample_rate=16000 -t 3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | ncat localhost 3000
```

Expect: Possibly no meaningful text (tone only) but no crashes.

## 8. Stopping

- Press Ctrl+C in the server terminal. You should see `Server Stopped`.
- Deactivate venv: `deactivate` (optional).

## Troubleshooting

| Symptom                       | Cause                               | Fix                                                                                                         |
| ----------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `ncat` not found              | PATH missing                        | Ensure Nmap install dir (e.g. `C:\Program Files (x86)\Nmap`) in PATH or copy `ncat.exe` next to ffmpeg exe. |
| `ffmpeg` not found            | Not installed / PATH                | Install ffmpeg, reopen terminal.                                                                            |
| Connection closes immediately | No audio piped / wrong port         | Verify using `localhost 3000` and server log shows Listening.                                               |
| No JSON output                | Silence / unsupported content early | Try a clearer speech MP3 or longer clip.                                                                    |
| High latency                  | Large model or CPU only             | Use `--model tiny` or enable GPU (`--use_gpu True`).                                                        |

## Validation Checklist

- Server starts without import errors.
- Receives raw PCM over TCP without crash.
- Emits JSON with expected fields (language, start, end, text).
- Graceful shutdown via Ctrl+C.

## Notes

- Sentence trimming & tokenizer dependencies removed; only segment-based 15s buffer trimming now.
- Output JSON schema is frozen; do not alter for manual tests.
