@echo off
REM Minimal Windows launcher for local testing
REM Usage: double-click or run in terminal

set MODEL=NbAiLab/nb-whisper-large
set HOST=0.0.0.0
set PORT=8000
set LOG_LEVEL=INFO
set LANGUAGE=no

python whisper_online_server.py ^
  --backend faster-whisper ^
  --model %MODEL% ^
  --model_cache_dir .\models ^
  --lan %LANGUAGE% ^
  --host %HOST% ^
  --port %PORT% ^
  --log-level %LOG_LEVEL% ^
  --min-chunk-size 1