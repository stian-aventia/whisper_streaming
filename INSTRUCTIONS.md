# Developer Instructions (Continuation Guide)

Purpose: Enable seamless continuation of work (Phase 2 onward) with small, readable, traceable commits. Every meaningful change must update both `CHANGELOG.md` (Unreleased) and `TODO.md`. After completing a cohesive feature/removal set, cut a new release (tag + changelog promotion).

## Current State
- Branch: `minimal-changes`
- Latest Release: `v1.1.0` (Phase 1 complete: backend & CLI simplification + warm-up changes)
- Output protocol: FROZEN (JSON lines unchanged).
- Active Next Focus: Phase 2 (Remove sentence trimming & tokenizer path) per `TODO.md`.

## Principles
1. Small commits (logical, minimal surface) – avoid mixing refactor + behavior changes.
2. Each commit message: `<type>(<area>): <summary>` (examples below).
3. After each multi-file removal or interface change: update `CHANGELOG.md` (category Added/Removed/Changed) and tick/annotate `TODO.md`.
4. Never change output JSON schema without explicit approval (would require major version bump).
5. Prefer feature flag / soft deprecation before hard removal unless clearly unused.
6. Keep diffs focused: do not reformat unrelated code.

## Commit Message Types In Use
- `feat`: new functionality (e.g. feature flag, new path)
- `refactor`: internal code movement/cleanup, no behavior change
- `perf`: performance improvements
- `fix`: bug fix or environment fix
- `chore`: release prep, tooling, meta updates
- `docs`: documentation-only changes

Examples:
```
feat(trim): add deprecation warning for --buffer_trimming
refactor(trim): remove sentence tokenizer logic
chore(deps): prune tokenizer packages from requirements
docs: update README removing sentence mode references
chore(release): prepare 1.2.0 changelog
```

## Phase 2 Execution Plan (Condensed)
1. Deprecate CLI flags (`--buffer_trimming`, `--buffer_trimming_sec`): accept but warn; internally force segment mode & 15s constant.
2. Remove sentence-mode branches (functions: `create_tokenizer`, `words_to_sentences`, `chunk_completed_sentence`, related conditionals) once deprecation commit landed & documented.
3. Prune dependencies: remove `mosestokenizer`, `wtpsplit`, `tokenize-uk` from `requirements.txt`.
4. Update container artifacts:
   - `entrypoint.sh`: drop removed flags & env vars.
   - `docker-compose.yaml`: remove obsolete `REPORT_LANGUAGE` (already) and any trimming variables (not yet present, verify).
   - `Dockerfile`: (optional in this step) remove clearly unused libs (future: openai-whisper, extra numerics) – can defer to a dedicated perf pass.
5. Documentation: strip sentence trimming references from both READMEs.
6. Update `CHANGELOG.md` (Unreleased): Removed (sentence mode + tokenizer deps), Changed (CLI flag removal), Added (hardcoded segment trimming constant).
7. Release `v1.2.0` once all above merged.

## Safety / Validation Steps
- Before removal: grep for `create_tokenizer`, `buffer_trimming`, `words_to_sentences` to ensure no hidden usage.
- After changes: run a short end-to-end container test with RTMP/pipe or piping a small raw PCM stream – confirm JSON output unchanged.
- (Optional) Save a baseline transcript file pre-change and diff post-change (expect identical text sequences).

## Release Process (Repeatable)
1. Finalize Unreleased section: ensure no empty categories (remove empties).
2. Decide next version (minor bump for removals that do not affect protocol: 1.1.0 -> 1.2.0).
3. Commit: `chore(release): prepare 1.2.0 changelog`.
4. Tag: `git tag -a v1.2.0 -m "Phase 2 complete: remove sentence mode"`.
5. Push: `git push origin minimal-changes --tags`.
6. Start new Unreleased section (already automated by changelog edit).

## Checklist Template (Per Change)
```
[ ] Implement code change
[ ] Update/verify tests or add quick smoke (if applicable)
[ ] Update TODO.md (tick / note)
[ ] Update CHANGELOG.md (Unreleased)
[ ] Build & run docker locally (if runtime path touched)
```

## Quick Smoke Test (Manual)
```
ffmpeg -f lavfi -i sine=frequency=440:sample_rate=16000 -t 3 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc localhost 3000
```
Expect: Possibly empty or minimal text (tone) – ensures pipeline stability (no crash). For speech, use a short spoken wav piped similarly.

## Pending Ideas (Not in Scope Yet)
- PCM fast path (Phase 3) feature flag `WS_RAW_PCM`.
- Structured metrics (latency, segments/sec) logging.
- Packaging (pyproject + entry points) after refactors stabilize.

## Do Not
- Introduce new external service calls without configuration knobs.
- Change JSON field names or ordering.
- Force GPU-only behavior.

## Questions / Escalation
If an ambiguity arises (e.g., whether a removal is safe), prefer adding a soft deprecation warning commit first, then follow with removal once confirmed unused.

---
Document owner: Initial version created at v1.1.0 + Phase 2 planning.
