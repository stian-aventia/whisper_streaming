## Copilot Instructions (Essential Guardrails)

This project has a frozen external interface. Assistants MUST respect the invariants below and defer to authoritative sources for anything dynamic.

### 1. Always Read These First

Before proposing or making any change, consult:

1. `README.md` (usage, env vars, protocol description)
2. `CHANGELOG.md` (Unreleased section for pending work)
3. `TODO.md` (current roadmap / open phases)

Do not rely on stale assumptions inside this file for project status—those three documents are the source of truth for evolving tasks.

### 2. Hard Invariants (Do NOT break)

| Area             | Rule                                                                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Output protocol  | One JSON object per line, keys in order: `language`, `start`, `end`, `text`. No new keys, no reordering, no whitespace guarantees added. |
| Timing semantics | Segment trimming window is a fixed internal constant (15s). Never expose or change it without explicit instruction.                      |
| Input format     | Only raw 16 kHz mono PCM16LE over TCP. No embedded media pulling, transcoding, or ffmpeg integration.                                    |
| Warm-up          | Local model silent warm-up stays enabled (improves first latency). Do not remove or disable.                                             |
| Dependencies     | Do NOT reintroduce removed tokenizer stack or ffmpeg/netcat. Avoid heavy new deps.                                                       |
| Logging          | No noisy debug by default; INFO-level additions must not flood output.                                                                   |
| Threading        | No new concurrency primitives unless explicitly requested.                                                                               |
| Trimming         | Only segment-based logic; no sentence/tokenizer mode revival.                                                                            |
| Env surface      | Prefer existing env vars; new ones require justification & CHANGELOG/TODO updates.                                                       |

### 3. Change Discipline

- Make minimal, focused diffs (one concern per commit).
- If a change affects ingest, buffering, or transcript ordering, STOP and request confirmation.
- Update both `CHANGELOG.md` (Unreleased) and `TODO.md` when completing or adding scoped work.
- Preserve CLI argument semantics; adding or removing flags requires explicit approval.

### 4. Commit Message Format

`<type>(<area>): <concise summary>`
Types: feat, refactor, perf, fix, chore, docs.
Examples:

- perf(ingest): reduce extra copy in PCM conversion
- fix(server): preserve accept loop after client reset
- docs(readme): clarify raw PCM input format

### 5. Safety Checklist Before Merge

1. Grep / search for removed symbols (avoid stragglers).
2. Local run with a tiny model: confirm starts, warm-up log, first transcript line appears.
3. If ASR pathway touched: compare a baseline short sample—transcripts must be identical (text + ordering).
4. Confirm JSON line ordering unchanged (spot check one output line).
5. Ensure `CHANGELOG.md` Unreleased updated; no unrelated noise in diff.

### 6. Environment Variables (Reference Only)

See `README.md` for authoritative list. Common ones: `MODEL`, `MODEL_CACHE_DIR`, `BACKEND`, `LANGUAGE`, `LOG_LEVEL`, `MIN_CHUNK_SIZE`, `SAMPLING_RATE`, `USE_GPU`, `MAX_SINGLE_RECV_BYTES`, `PACKET_SIZE_BYTES`, `SUPPRESS_PKG_RES_WARN`.
Do not silently repurpose an existing variable.

### 7. What NOT To Do (Without Explicit Request)

- Add new JSON fields or reorder existing ones.
- Expose or modify the 15s trim constant.
- Reintroduce sentence/tokenizer or offline simulation modes.
- Embed ffmpeg / pulling media internally.
- Introduce threads, async refactors, or multi-client concurrency logic.
- Downgrade or remove warm-up.

### 8. Escalation Triggers

Immediately ask for confirmation if work might:

- Alter transcript timing, segmentation, or ordering.
- Change memory footprint of the rolling 15s window.
- Add dependencies > a few MB (wheel size) or require system packages.
- Modify env/CLI surface externally consumed.

### 9. Fast Triage Guidance

| Symptom         | Usual Cause                              | Quick Check                              |
| --------------- | ---------------------------------------- | ---------------------------------------- |
| No transcripts  | MIN_CHUNK_SIZE too large or silent input | Lower MIN_CHUNK_SIZE / verify bytes flow |
| First line slow | Warm-up missing                          | Confirm warm-up log line                 |
| Large memory    | Trim window altered or leak              | Verify constant still 15s                |
| High CPU        | Extra copies in ingest                   | Inspect PCM conversion path              |

### 10. Release Hygiene

When finalizing a release:

1. Move Unreleased entries into a dated version block.
2. Reset Unreleased headings.
3. Tag + push; optional release notes file can mirror CHANGELOG section.

### 11. Source of Truth for Roadmap

Roadmap & open tasks intentionally live ONLY in `TODO.md`. Do not duplicate phase lists here; just reference them when needed.

### 12. Minimal Assistant Startup Routine

On new session:

1. Read `README.md`, `CHANGELOG.md` (Unreleased), `TODO.md`.
2. List invariants (section 2) mentally before editing.
3. Apply smallest diff; run safety checklist.

---

This document is intentionally lean: it encodes the non-negotiable guardrails. Dynamic status lives in README / CHANGELOG / TODO.
