# TODO / Technical Refactor Plan

Scope: Minimal refactor to support only required functionality for live transcription with 10s delay. NO CHANGE to current output protocol (JSON line format remains exactly as-is; downstream client hard-coded).

## Guiding Principles
- Preserve external behaviour (output lines, timing semantics) unless explicitly approved.
- Reduce code surface & dependencies.
- Improve maintainability and performance of audio ingestion + backend selection.
- Keep incremental, commit small cohesive steps.

## Phase 1: Backend & CLI Simplification
- [x] Remove unsupported backends: `WhisperTimestampedASR`, `MLXWhisper`.
- [x] Remove `VACOnlineASRProcessor` (Silero VAD controller) and related args (`--vac`, `--vac-chunk-size`).
- [x] Restrict `--backend` choices to: `faster-whisper`, `openai-api`.
- [x] Remove `--report-language` option (unused); use existing --lan for output language fallback 'en'.
- [x] Keep `--vad` flag (only meaningful for faster-whisper; ignored for OpenAI) and set default enabled (default=True).
- [ ] Update `CHANGELOG` (Unreleased) with Removed/Changed entries (mark internal only; no protocol change).

## Phase 2: Audio Ingestion Optimization
- [ ] Replace per-chunk RAW decode pipeline (soundfile + librosa) with direct PCM16 → float32 via `np.frombuffer`.
- [ ] (future) Replace librosa in streaming path; warm-up now silent (no file dependency).
- [ ] Add minimal validation: ensure even byte length; discard leftover partial sample if any.
- [ ] Add guard for oversized single recv (log warning if > X MB configurable?).

## Phase 3: Server Loop Hygiene
- [ ] Clarify receive loop semantics: distinguish "no data yet" vs "stream ended" return values.
- [ ] Add socket timeout (e.g. 30s) to avoid hanging connections.
- [ ] Increase `listen()` backlog (e.g. 5) for modest concurrency (still serial handling unless threaded later).
- [ ] Prepare hooks for optional future multi-client handling (no implementation yet).

## Phase 4: Internal Cleanup
- [ ] Remove global variables where feasible (`running`, `server_socket`) – encapsulate in a Server class.
- [ ] Narrow imports (delay heavyweight imports until needed; e.g. OpenAI only when that backend chosen).
- [ ] Type hints for public functions in `whisper_online_server.py` & key classes.
- [ ] Inline small helper logic where it reduces indirection without harming clarity.

## Phase 5: Testing & Observability (Non-breaking)
- [ ] Add lightweight smoke script to feed a few seconds of test PCM and assert non-empty JSON lines.
- [ ] Log model load time + average process_iter latency every N iterations.
- [ ] (Optional) Add environment variable override for log level.

## Phase 6: Documentation
- [ ] Update README to reflect supported backends only.
- [ ] Document silent warm-up and required input audio format (16kHz mono PCM16LE streaming).
- [ ] Add note that output format is frozen for downstream compatibility.

## Deferred / Out of Scope For Now
- Output JSON augmentation (language, confidence, final flag) – explicitly deferred.
- Full multi-client concurrency & thread safety.
- HTTP health endpoint.
- Refactoring directory structure into modular packages.

## Risk / Mitigation
| Risk | Mitigation |
|------|------------|
| Removing backends breaks unknown user workflows | Per branch only; tag new major when merging to main if needed |
| Audio path refactor introduces scaling bug | Add quick test comparing RMS before/after change |
| Accidentally changing output formatting | Add a regression test capturing one sample line & diff strictly |

## Quick Regression Test Ideas (Later)
- Feed synthetic sine + short speech frame → ensure at least one non-empty transcript segment.
- Warmup file path invalid → (removed feature) now irrelevant.

## Execution Order (Granular Commits)
1. Remove backends & VAC classes + CLI prune + CHANGELOG update.
2. Introduce optimized PCM ingestion (guarded by feature flag env `WS_NEW_PCM=1` then flip default).
3. Server loop semantic cleanup (timeouts, backlog).
4. Internal globals reduction & typing.
5. Add smoke test script + README/CHANGELOG updates.

## Tracking
Use checklist ticks as tasks complete; update if scope shifts.

