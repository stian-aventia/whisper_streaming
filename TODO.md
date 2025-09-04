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
- [x] Update `CHANGELOG` (Unreleased) with Removed/Changed entries (mark internal only; no protocol change).

## Phase 2: Remove Sentence Trimming & Tokenizer Path

Goal: Simplify buffer management by dropping under-performing/unused "sentence" trimming mode and associated tokenizers. Retain only segment-based trimming with a fixed internal threshold.

Rationale:

- "sentence" requires multiple optional deps (mosestokenizer, wtpsplit, tokenize_uk) increasing image size and cold start.
- No robust Norwegian splitter available; inconsistent quality across languages.
- Segment-based trimming (using model segments) is simpler, deterministic, and already default.
- Reduces branching and cognitive load in `OnlineASRProcessor`.

Scope (No change to external JSON output format):
Meta:

- [x] Add developer instructions file (`INSTRUCTIONS.md`) for continuation workflow.

1. CLI Cleanup:
   - [x] Remove `--buffer_trimming` option entirely.
   - [x] Remove `--buffer_trimming_sec`; hardcode constant (15s) as module-level `SEGMENT_TRIM_SEC = 15`.
2. Code Removal:
   - [x] Delete `create_tokenizer` function and related WHISPER_LANG_CODES.
   - [x] Remove tokenizer parameter & logic from `OnlineASRProcessor`.
   - [x] Remove `words_to_sentences`, `chunk_completed_sentence`, and sentence-specific branch in `process_iter`.
3. Dependency Prune:
   - [x] Drop tokenizer-related packages from `requirements.txt` (mosestokenizer, wtpsplit, tokenize-uk).
4. Container / Deployment Updates:
   - Dockerfile: remove now-unused tokenizer deps if previously added; (optionally) stop pre-installing openai-whisper & unused libs (follow-up optimization) – at minimum ensure no reference to sentence trimming remains in comments.
   - entrypoint.sh: drop `--buffer_trimming` and `--buffer_trimming_sec` arguments & related env expansion vars.
   - [x] docker-compose.yaml: remove `REPORT_LANGUAGE`, ensure minimal env list (LANGUAGE kept).
   - Verify image still builds and container starts with simplified arguments.
5. Documentation Alignment:
   - Update README files to remove references to sentence trimming and related environment variables.
6. Documentation:
   - Update both `README.md` and `README_ORG.md` to eliminate sentence trimming references.
   - Note in CHANGELOG (Removed: sentence trimming mode & tokenizer dependencies; Changed: CLI options `--buffer_trimming*` removed).
7. Backward Compatibility Note:
   - Since we are on a feature branch and output protocol unchanged, treat as minor bump (planned 1.2.0). If any external automation passed `--buffer_trimming`, they'll now error—document clearly.
8. Testing / Validation:
   - Quick diff: run before & after on same audio ensuring identical sequence of emitted segment texts (ignoring timing jitter <20ms).
9. Cleanup:
   - Remove lingering imports (librosa retained for offline simulation only for now).

Risks & Mitigation:
| Risk | Impact | Mitigation |
|------|--------|------------|
| External scripts still pass `--buffer_trimming` | Runtime error | Explicit error message in argparse removal commit; mention in CHANGELOG |
| Timing shift due to earlier trimming differences | Minor latency / buffer size change | Keep same numeric threshold (15s) and segment logic unchanged |
| Hidden dependency use of tokenizer elsewhere | Import error | Grep repo for `create_tokenizer` & tokenizer packages before final removal |

Planned Commits:

1. feat(trim): deprecate `--buffer_trimming` (warn if used) & hardcode segment mode
2. refactor(trim): remove sentence code paths & tokenizers
3. chore(deps): prune tokenizer deps from requirements.txt
4. docs: update READMEs + CHANGELOG Unreleased
5. clean: remove deprecation warning stub (if any)

Success Criteria:

- No imports of mosestokenizer / wtpsplit / tokenize_uk.
- Running server without previous flags works identically (segment trimming still applied at 15s).
- CHANGELOG reflects removal.

## Phase 3: Remove Source Stream & Single-File Simulation

Goal: Focus codebase exclusively on the persistent TCP server. Remove embedded ffmpeg pull + local simulation/offline modes to simplify runtime, shrink image, and reduce maintenance.

Scope:

- [x] Remove `--source-stream` argument and related environment variable handling (entrypoint + server code + compose comments).
- [x] Delete / refactor out: `run_subprocess`, `worker_thread`, ffmpeg command assembly, thread launch logic in `whisper_online_server.py`.
- [x] Remove dependency on `ffmpeg` and `netcat` from Dockerfile once feature removed (move apt purge to same commit if safe, else subsequent commit in phase).
- [x] Remove standalone file simulation & offline modes:
  - [x] Eliminate `whisper_online.py` CLI execution block.
  - [x] Remove arguments: `audio_path`, `--offline`, `--comp_unaware`, `--start_at`.
  - [x] Prune logic branches tied to simulation timing.
- [x] Update docs (`README.md`, `README_ORG.md`, `TEST.md`) to describe only server usage (TCP raw PCM input) and external ffmpeg piping examples. (README + TEST updated; README_ORG left as archival.)
- Update CHANGELOG (Unreleased): Removed (source-stream internal ingest, offline simulation modes & related CLI args, file-based runner).
- Adjust Docker image (drop ffmpeg/netcat). Provide external usage example for pulling RTMP outside container.

Risks & Mitigation:
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hidden usage of `--source-stream` in deployment scripts | Break ingest automation | Communicate in changelog; add transitional error message for one release if needed (decide before merge) |
| Some teams using offline simulation for benchmarking | Lose quick test path | Provide a separate sample script or doc snippet using existing classes before removal (optional) |
| ffmpeg removal breaks accidental internal tests | Minor | Add doc note with external ffmpeg pipe examples |

Planned Commits (suggested):

1. refactor(stream): isolate backend classes from `whisper_online.py` into `src/` (optional preparatory step).
2. feat(stream): remove `--source-stream` path & thread logic (update CHANGELOG/TODO).
3. feat(sim): remove offline / file simulation CLI & flags.
4. chore(docker): drop ffmpeg & netcat from Dockerfile, remove env vars from compose/entrypoint.
5. docs(stream): update READMEs/TEST with external ffmpeg piping examples only.

Success Criteria:

- No references to `SOURCE_STREAM`, `--source-stream`, offline/comp_unaware flags, or `audio_path` CLI.
- Docker image no longer installs ffmpeg/netcat.
- Server still starts and processes incoming raw PCM.
- CHANGELOG reflects removals.

## Phase 4: Faster-Whisper Model Parameter Consolidation

- [x] Remove `--model_dir`; single `--model` now handles builtin size, path or HF repo id.
- [x] Bug: Server exits entirely when client/stream disconnects. Keep listening on the port and accept new connections until explicit shutdown.
- [x] Improved Ctrl+C (SIGINT) handling: clean shutdown, release socket, consistent final log line (no residual globals).

Phase 4 core items completed (further refinements, if any, will be tracked separately).

## Phase 5: Audio Ingestion Optimization

- [ ] Replace per-chunk RAW decode pipeline (soundfile + librosa) with direct PCM16 → float32 via `np.frombuffer`.
- [ ] (future) Replace librosa in streaming path; warm-up now silent (no file dependency).
- [ ] Add minimal validation: ensure even byte length; discard leftover partial sample if any.
- [ ] Add guard for oversized single recv (log warning if > X MB configurable?).

## Phase 6: Server Loop Hygiene

- [ ] Clarify receive loop semantics: distinguish "no data yet" vs "stream ended" return values.
- [ ] Add socket timeout (e.g. 30s) to avoid hanging connections.
- [ ] Increase `listen()` backlog (e.g. 5) for modest concurrency (still serial handling unless threaded later).
- [ ] Prepare hooks for optional future multi-client handling (no implementation yet).

## Phase 7: Internal Cleanup

- [ ] Remove global variables where feasible (`running`, `server_socket`) – encapsulate in a Server class.
- [ ] Narrow imports (delay heavyweight imports until needed; e.g. OpenAI only when that backend chosen).
- [ ] Type hints for public functions in `whisper_online_server.py` & key classes.
- [ ] Inline small helper logic where it reduces indirection without harming clarity.

## Phase 8: Testing & Observability (Non-breaking)

- [ ] Add lightweight smoke script to feed a few seconds of test PCM and assert non-empty JSON lines.
- [ ] Log model load time + average process_iter latency every N iterations.
- [ ] (Optional) Add environment variable override for log level.

## Phase 9: Documentation

- [ ] Update README to reflect supported backends only.
- [ ] Document silent warm-up and required input audio format (16kHz mono PCM16LE streaming).
- [ ] Add note that output format is frozen for downstream compatibility.

## Deferred / Out of Scope For Now

- Output JSON augmentation (language, confidence, final flag) – explicitly deferred.
- Full multi-client concurrency & thread safety.
- HTTP health endpoint.
- Refactoring directory structure into modular packages.

### Deferred (Post v1.2) Container / Image Improvements

- (done) Switch base image to `python:3.12-slim` (libsndfile1 installed for soundfile).
- (done)Add `.dockerignore` to exclude model snapshots, caches, venv, pyc files from build context.
- Consider multi-stage build (builder for wheels, runtime slim) and/or separate GPU Dockerfile with torch + cudnn.
- Add simple healthcheck (e.g. TCP connect script or lightweight Python probe) for orchestration readiness.
- Pin base image by digest for reproducibility & to reduce vulnerability scan noise between patch releases.
- Optionally generate requirements lock (`pip compile` / hashes) once dependency set stabilizes.
- (done)Explore dropping `hf_xet` if confirmed unused at runtime (follow-up verification required).
- (done)Review and remove temporary `setuptools<81` pin once ctranslate2/faster-whisper drop pkg_resources usage.
- (done)Remove `--source-stream` ingestion path: delete ffmpeg/ncat runtime dependency, associated thread + subprocess helpers in `whisper_online_server.py`, and apt installs (ffmpeg, netcat) from Dockerfile; require external ffmpeg piping instead (will further slim image). (Planned after confirming no internal usage.)

## Risk / Mitigation

| Risk                                            | Mitigation                                                      |
| ----------------------------------------------- | --------------------------------------------------------------- |
| Removing backends breaks unknown user workflows | Per branch only; tag new major when merging to main if needed   |
| Audio path refactor introduces scaling bug      | Add quick test comparing RMS before/after change                |
| Accidentally changing output formatting         | Add a regression test capturing one sample line & diff strictly |

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
