## v1.5.1 – Inkrementelle ytelses- og DX‑forbedringer (ingen protokollendringer)

Dato: 2025-09-04

### Added
- Oversized packet guard (`MAX_SINGLE_RECV_BYTES`) varsler ved store enkeltmottak.
- Validering av PCM-pakker (dropper trailing odd byte).
- `PACKET_SIZE_BYTES` miljøvariabel for å tune mottaksbuffer (samme default som før).
- Varsel dersom `--min-chunk-size` > internt 15s trim-vindu.

### Changed
- Opprydding: fjernet ubrukte variabler (`size`, `min_chunk`) og legacy `io` import.
- Type hints for PCM-dekoder og mottaksloop (intern forbedring, ingen runtime‑endring).
- `local_build.ps1`: single-arch som default; multi-arch via `-MultiArch` (+ ev. `-Push`).
- `local_run.ps1`: bedre defaults + GPU flagg, cache-mount og ekstra env.

### Removed
- Avhengighet `librosa` i streaming path (erstattet av direkte PCM16→float32).

### Fixed
- Undertrykker støyende `pkg_resources` DeprecationWarning (kan deaktiveres med `SUPPRESS_PKG_RES_WARN=0`).
- Optimalisert direkte PCM16→float32 ingest (ingen endring i utdataformat).
- Korrigert port‑mapping i `local_run.ps1` (tidligere kunne `-p` falle ut).

### Security
- Ingen endringer.

### Compatibility
- JSON linjeformat og feltrekkefølge uendret.
- Warm-up beholdt.

### Upgrade Notes
- Ingen tiltak nødvendig. Klienter fungerer uendret.
- Juster `PACKET_SIZE_BYTES` kun ved spesielle nettverksforhold.

---
For komplett historikk se `CHANGELOG.md`.