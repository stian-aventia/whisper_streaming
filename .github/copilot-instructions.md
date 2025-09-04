# Copilot Instructions

Purpose: Guide AI code assistants to make safe, minimal, high‑value changes without breaking the frozen external protocol.

## Immutable External Contract

- Output = newline‑delimited JSON objects. Field names, order, spelling, and timing semantics MUST NOT change.
- Segment trimming window fixed internally at 15s (do not expose a flag or change constant unless explicitly asked).
- Accepts raw 16 kHz mono PCM16LE audio over TCP (server only). No embedded ffmpeg ingest; any media pull happens outside.

## Current Scope / Completed

- Removed: sentence tokenizer mode, offline simulation, internal source-stream ingestion, ffmpeg & netcat runtime deps, unused line receive helpers.
- Backends supported: `faster-whisper`, `openai-api`.
- Warm-up silence still performed for local model to mitigate first-latency.

## Near-Term (Phase 4 Targets)

1. Consolidate model params: drop `--model_dir`; single `--model` passed directly to `WhisperModel` (may be name, local path, or HF repo id). Keep `--model_cache_dir`.
2. Server robustness: keep listening after client disconnect (loop accept again) until explicit shutdown.
3. Graceful Ctrl+C: clean socket close, deterministic final log line.

## Mid-Term (Later Phases – DO NOT START UNPROMPTED)

- PCM ingestion optimization (replace librosa/soundfile path with direct numpy frombuffer).
- Receive loop hygiene (timeouts, backlog, clearer semantics, optional multi-client prep).
- Internal cleanup (remove globals, add typing, lazy imports).
- Lightweight smoke test + basic metrics logging.
- Documentation refresh & eventual removal of temporary setuptools<81 pin once upstream fixed.

## Coding Principles

- Small, focused diffs; never mix refactor + behavior change.
- Update BOTH `CHANGELOG.md` (Unreleased) and `TODO.md` when completing a planned item.
- Preserve public CLI argument behavior unless change is explicitly in scope.
- Avoid introducing new heavy dependencies; prefer stdlib or existing libs.
- No silent output format tweaks (even reordering JSON keys is forbidden).

## Commit Message Style

`<type>(<area>): <concise summary>`
Types: feat, refactor, perf, fix, chore, docs.
Examples:

- refactor(model): remove --model_dir flag and related branching
- feat(server): keep accepting new clients after disconnect
- fix(shutdown): ensure graceful SIGINT closes socket

## Safety Checklist (Before Merging Changes)

- Grep for removed symbol usages (e.g., if dropping a flag) to ensure no leftovers.
- Run container locally with small model to confirm startup + first transcription.
- Compare a short baseline transcript (text only) if touching ASR path – must match exactly.

## Implementation Hints

- Model consolidation: map old `--model_dir` logic into direct pass-through; if both provided, prefer `--model` and log warning until `--model_dir` removed.
- Listener persistence: wrap accept+serve in while running loop; on client disconnect, continue; only break on global shutdown flag.
- Ctrl+C: register signal handler setting a flag; ensure server socket closed once; avoid broad except; flush final log.

## Things NOT To Do

- Do not reintroduce sentence/tokenizer dependencies.
- Do not add ffmpeg or netcat back into the image.
- Do not change trimming constant or expose new trimming flags.
- Do not alter JSON ordering, keys, or add new fields.
- Do not introduce threads unless explicitly requested (keep simplicity).

## Preferred Order When Asked For Phase 4

1. Add transitional handling (accept --model_dir but deprecate) – update docs.
2. Implement persistent server accept loop.
3. Improve SIGINT shutdown.
4. Remove deprecated flag in a follow-up commit (if user confirms).

## Observability (Optional, Only If Requested)

- Log: model load duration, average processing latency (rolling mean) – behind a simple env flag.

## Temporary Pins / Follow-ups

- setuptools<81 pinned due to ctranslate2/pkg_resources deprecation path; remove once upstream resolves. Track in `TODO.md`.

## Escalation

If a change might affect transcript timing or ordering, stop and request explicit confirmation before proceeding.

---

This file is authoritative for AI assistants; keep it updated when constraints or phases change.
