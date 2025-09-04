# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.0.0/) and this project adheres (as far as possible) to Semantic Versioning (https://semver.org/) starting from its first tagged release.

Origin: This repository is a fork / adaptation of the original UFAL whisper streaming server:
https://github.com/ufal/whisper_streaming

## [Unreleased]

### Added

- (planned) Direct PCM16→float ingestion (Phase 4) – not yet implemented.

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.3.0] - 2025-09-04

### Added

- Consolidated manual Windows test instructions into primary README (previously `TEST.md`).

### Changed

- Internal server simplified: removed dormant source-stream code paths (ffmpeg thread logic).
- Docker image slimmer: dropped runtime installation of ffmpeg and netcat (external piping required).
- Base image switched to python:3.12-slim (added libsndfile1 only).
- Documentation: merged `TEST.md` manual guide into primary `README.md` (removed separate file for clarity).

### Deprecated

- (none)

### Removed

- `--source-stream` argument and internal ffmpeg/netcat ingestion pipeline.
- Bundled ffmpeg and netcat from container image.
- Offline/simulation CLI paths in `whisper_online.py` (module is now server-only support code).
- Unused line receive helpers (`receive_one_line`, `receive_lines`) and `Connection.receive_lines` method.
- Replaced local_build.sh / local_run.sh with Windows PowerShell scripts `local_build.ps1` and `local_run.ps1`.

### Fixed

- Nothing.

### Security

- Nothing.

## [1.2.0] - 2025-09-04

### Added

- Developer continuation guide `INSTRUCTIONS.md`.
- Fixed segment trimming threshold constant (15s) internal `SEGMENT_TRIM_SEC`.

### Changed

- CLI simplified: buffer trimming now always segment-based with fixed 15s threshold.
- Docker image streamlined: install via `requirements.txt` only; removed unused extras (openai-whisper, tiktoken, tqdm, more-itertools, numba layers).
- Documentation reorganized: archived original upstream READMEs under `docs/orig/` with root stub pointer.

### Deprecated

- (none)

### Removed

- CLI options `--buffer_trimming`, `--buffer_trimming_sec`.
- Sentence trimming mode and related tokenizer logic (`create_tokenizer`, `words_to_sentences`, `chunk_completed_sentence`).
- Tokenizer dependency chain: mosestokenizer, wtpsplit, tokenize-uk.
- Deprecated `REPORT_LANGUAGE` environment variable from compose (use `LANGUAGE`).

### Fixed

- Nothing.

### Security

- Nothing.

## [1.1.0] - 2025-09-04

### Added

- (internal) Refactor groundwork (cleanup branch scaffolding).

### Changed

- Default for `--vad` flag set to enabled (True) for local faster-whisper backend. (No protocol/output change.)

### Removed

- Legacy backends: `WhisperTimestampedASR`, `MLXWhisper`.
- Silero-based VAC processing (`VACOnlineASRProcessor`) and related CLI flags `--vac`, `--vac-chunk-size`.
- CLI flag `--report-language` (language field now derives from `--lan` with fallback to 'en').
- CLI flag `--warmup-file` and bundled sample `samples_jfk.wav` (replaced by internal silent warm-up for local backend).

### Fixed

- Docker runtime script failure on Windows clones: normalize line endings & chmod entrypoint.

### Security

- N/A

## [1.0.0] - 2025-07-15

### Added

- Baseline imported from commit e80686ec07db213bdb3fcabcb7092b3e27e22bf5 of the original implementation ("Fixed gpu support and updated README (#2)").

### Notes

- This provisional version mirrors upstream without local modifications.

---

### Release Process (internal guidelines)

1. Update "Unreleased" section: move relevant entries under a new version heading with date (YYYY-MM-DD).
2. Keep category subsections even if empty during drafting; prune empty ones on release.
3. Ensure all external changes reference an issue / PR number when available (e.g. `(#42)`).
4. After tagging, add comparison links at bottom.

### Categories Legend

Use: Added, Changed, Deprecated, Removed, Fixed, Security.

## Link References

[Unreleased]: https://github.com/stian-aventia/whisper_streaming/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/stian-aventia/whisper_streaming/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/stian-aventia/whisper_streaming/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/stian-aventia/whisper_streaming/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ufal/whisper_streaming/tree/e80686ec07db213bdb3fcabcb7092b3e27e22bf5
