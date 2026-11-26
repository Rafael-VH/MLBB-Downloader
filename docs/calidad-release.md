# Calidad, release y legal

## Estado actual

| Área | Estado |
|---|---|
| Tests | ✅ 91 passed (`uv run pytest`) |
| Lint | ✅ ruff check clean |
| Arquitectura guardrail | ✅ `tests/test_architecture.py` |
| CI GitHub Actions | ⚠️ workflows base (`ci.yml`, `release.yml`), pendiente validación real |
| PyInstaller | ⚠️ spec base + smoke build local OK; pendiente máquina limpia |
| LICENSE | ✅ MIT |
| CHANGELOG | ✅ presente |

## Estrategia de tests

### Existentes

- Unit: manifest, paths/slug, keying, client retry/throttle, envelope, engine, images extraction, progress, registry, reporting.
- Integración mockeada: heroes/academy/images usecases con `MockTransport/respx`.
- CLI smoke: comandos registrados, errores API formateados, reporte JSON.
- GUI smoke: import/instanciación offscreen (PySide6).
- Arquitectura: dominio puro.

### Faltantes recomendados

- Smoke live opt-in (`LIVE_API_TESTS=1`) para 1-2 héroes.
- Tests CLI end-to-end más amplios para `sync/check` top-level con mocks.
- Smoke build PyInstaller en VM limpia.
- Validación real de workflows en GitHub Actions.

## CI

### `ci.yml`

- `uv sync --dev`
- `uv run ruff check src tests scripts`
- `uv run pytest`

### `release.yml` (tag `v*`)

- build Windows con `uv sync --extra gui --extra packaging --dev`
- `uv run pytest`
- `uv run pyinstaller packaging/mlbb-downloader.spec --noconfirm`
- checksums SHA256
- adjunta artefactos a GitHub Release

## Packaging

- Target inicial: Windows.
- PyInstaller: `--windowed --onefile` (spec `packaging/mlbb-downloader.spec`).
- Datos/config/logs en `%APPDATA%/MLBBDownloader/`.
- Smoke local verificado: `dist/MLBBDownloader.exe` (~54 MB), arranque offscreen 5s sin crash.
- Pendiente: verificación en VM limpia sin Python y validación visual/assets Qt.

## Legal / cumplimiento

- Proyecto no oficial, no afiliado a Moonton.
- Marcas y assets pertenecen a sus dueños.
- Fuente de datos: Rone Arena API / servicios públicos del juego.
- No embeber secretos/tokens.
- Tokens de usuario solo opt-in, storage seguro, nunca en logs.

## Checklist antes de release

- [x] `LICENSE` MIT
- [x] `CHANGELOG.md`
- [x] Disclaimer visible en README y GUI
- [x] Sin secretos en repo/logs/artefactos
- [ ] CI verde en GitHub Actions
- [ ] Smoke live opt-in documentado
- [ ] PyInstaller build verificado en máquina limpia
- [ ] Checksum publicado
