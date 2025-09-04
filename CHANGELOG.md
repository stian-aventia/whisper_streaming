# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.0.0/) and this project adheres (as far as possible) to Semantic Versioning (https://semver.org/) starting from its first tagged release.

Origin: This repository is a fork / adaptation of the original UFAL whisper streaming server:
https://github.com/ufal/whisper_streaming

## [Unreleased]
### Added
- (internal) Refactor groundwork (cleanup branch scaffolding).

### Changed
- Default for `--vad` flag set to enabled (True) for local faster-whisper backend. (No protocol/output change.)

### Deprecated
- Nothing.

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
[Unreleased]: https://github.com/stian-aventia/whisper_streaming/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ufal/whisper_streaming/tree/e80686ec07db213bdb3fcabcb7092b3e27e22bf5

