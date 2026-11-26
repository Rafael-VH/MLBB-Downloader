# Plan maestro

## Objetivo

Construir una aplicación Python (CLI primero, GUI al final) que descargue datos públicos de Mobile Legends: Bang Bang desde la Rone Arena API, con resume, verificación por hash, detección de cambios/faltantes/corrupción y empaquetado ejecutable.

## Estado actual (verificado)

| Área | Estado | Evidencia |
|---|---|---|
| Arquitectura | ✅ Hexagonal-lite aplicada | `domain/`, `adapters/`, `usecases/`, `cli.py`, `tests/test_architecture.py` |
| Cliente HTTP | ✅ | `adapters/arena.py` (gzip, delay, retries, paginación 1-based, `total` verificado) |
| Manifest/resume | ✅ | `domain/manifest.py` v2, `adapters/manifest_store.py`, `adapters/fsstore.py` |
| Check | ✅ | changed/new/missing/corrupted/not_downloaded/failed |
| Heroes JSON | ✅ parcial | index + 8 subrecursos por héroe; faltan rank/positions/wallpapers gallery |
| Academy JSON | ✅ | colecciones + per-hero con políticas UGC/redundante/discontinued |
| Imágenes | ✅ MVP | extraídas de JSON locales; sync/check; dedupe por URL canónica |
| Addon | ✅ | win-rate, ip |
| CLI Download/Check All | ✅ | `mlbb sync`, `mlbb check` |
| GUI | ❌ | fase final |
| Packaging/CI/release | ❌ | PyInstaller, workflows, LICENSE, CHANGELOG pendientes |
| User/auth | ❌ | opt-in, no implementado |

## Brechas prioritarias

### P1 — Completar cobertura pública (antes de GUI)

1. ~~**Heroes faltantes**~~: `/heroes/rank`, `/heroes/positions`, `/heroes/wallpapers` (galería) implementados.
2. ~~**Registry completo heroes**~~: HERO_SUBRESOURCES y colecciones registradas en `domain/registry.py`/`DESCRIPTORS`.
3. ~~**Registry validado contra OpenAPI**~~: `scripts/check_registry.py` compara registry vs OpenAPI; test interno de consistencia en `tests/test_registry.py`.
4. ~~**CLI por entidad**~~: `heroes sync/check --hero-id <id>` implementado.

### P2 — Operación y confiabilidad

5. ~~**`images check --local-only`**~~: `images check --local-only` y `check --local-only` verifican hash local sin fetch remoto.
6. ~~**`status` con corruptos**~~: `mlbb status --verify` rehashea archivos locales y reporta `corrupted`.
7. ~~**Reportes exportables**~~: `--report <path.json|md>` en comandos sync/check.
8. **Checkpoint de job**: `_progress.json` opcional para GUI/jobs largos; manifest ya cubre lo esencial.

### P3 — Entrega

9. **Compatibilidad GUI**: verificar PySide6 en Python 3.14.0; si falla, definir extra `gui` con pin de versión.
10. **GUI PySide6**: dashboard, tools por dominio, workers, progreso, cancel/pause, logs, settings.
11. **Packaging**: PyInstaller (`--windowed --onefile`), assets Qt, app data en `%APPDATA%/MLBBDownloader`.
12. **CI/Release**: lint/test/smoke build; release en tag `v*` con checksums.
13. **Legal/repo hygiene**: `LICENSE` MIT, `CHANGELOG.md`, disclaimer/atribución visible.

### P4 — Opcional / diferido

14. **User endpoints** (`/api/user`): opt-in explícito, sin tokens en logs, storage seguro.
15. **Esports**: fuera de alcance actual por decisión del usuario.

## Roadmap propuesto

| Milestone | Alcance | Salida |
|---|---|---|
| M1 Cobertura pública | rank/positions/wallpapers gallery, registry completo, CLI `--hero-id`, tests | CLI cubre mapa público de heroes |
| M2 Operación | local-only image check, status corruptos, reportes JSON/MD, smoke live opt-in | Mejor observabilidad |
| M3 GUI MVP | PySide6, main window, workers, sync/check all, progreso, logs, settings | App usable en escritorio |
| M4 Packaging | PyInstaller Windows, app data dir, release workflow, LICENSE/CHANGELOG | Ejecutable distribuible |
| M5 User/Auth | opt-in, keyring/almacenamiento seguro, separación de datos | Dominio sensible aislado |

## Criterios de aceptación

- [ ] `sync` descarga todos los endpoints públicos soportados sin intervención manual.
- [ ] `check` reporta new/changed/missing/corrupted sin descargar.
- [ ] Descargas reanudables e idempotentes; sin archivos corruptos finales.
- [ ] Sin secretos/tokens en logs.
- [ ] GUI no bloquea hilo principal.
- [ ] Ejecutable Windows corre en máquina limpia.
- [ ] README + docs + LICENSE + disclaimer presentes.

## Decisiones vigentes

- Esports: diferido/no prioritario.
- CLI primero; GUI al final.
- SHA-256 como señal de cambio (sin ETag/Last-Modified).
- Manifest v2 compatible con v1.
- Identidad de imagen por URL canónica (desenvuelve `wsrv.nl`).
- Work-unit commits en rama de feature; push solo por decisión del usuario.
