# Calidad, release y legal

## Estado actual

| Área | Estado |
|---|---|
| Tests | ✅ 76 passed (`uv run pytest`) |
| Lint | ✅ ruff check |
| Format | ✅ ruff format |
| Arquitectura guardrail | ✅ `tests/test_architecture.py` |
| CI GitHub Actions | ❌ pendiente |
| PyInstaller | ❌ pendiente |
| Release workflow | ❌ pendiente |
| LICENSE | ❌ pendiente (MIT declarada en pyproject) |
| CHANGELOG | ❌ pendiente |

## Estrategia de tests

### Existentes

- Unit: manifest, paths/slug, keying, client retry/throttle, envelope, engine, images extraction.
- Integración mockeada: heroes/academy/images usecases con `MockTransport/respx`.
- CLI smoke: comandos registrados, errores API formateados.
- Arquitectura: dominio puro.

### Faltantes recomendados

- Smoke live opt-in (`LIVE_API_TESTS=1`) para 1-2 héroes.
- Tests CLI end-to-end para `sync/check` top-level con mocks.
- Tests de corrupción/missing para status/reporting ampliado.
- Tests de Windows paths/case-insensitive si se agrega GUI/packaging.

## CI propuesto

### `ci.yml`

- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`
- build smoke (futuro): `uv run pyinstaller ...` en Windows runner

### `release.yml` (tag `v*`)

- build Windows `.exe`
- generar SHA256 checksums
- adjuntar artefactos a GitHub Release
- publicar changelog/notas

## Packaging

- Target inicial: Windows.
- PyInstaller: `--windowed --onefile` para GUI; CLI puede mantener modo console.
- Datos/config/logs en `%APPDATA%/MLBBDownloader/`, no junto al exe.
- Verificar en VM limpia sin Python.
- Riesgo conocido: **PySide6 en Python 3.14.0 no verificado**.

## Legal / cumplimiento

Incluir en README, GUI About y release:

- Proyecto no oficial, no afiliado a Moonton.
- Marcas y assets pertenecen a sus dueños.
- Fuente de datos: Rone Arena API / servicios públicos del juego.
- No embeber secretos/tokens.
- Tokens de usuario solo opt-in, storage seguro, nunca en logs.

## Checklist antes de release

- [ ] `LICENSE` MIT
- [ ] `CHANGELOG.md`
- [ ] CI verde
- [ ] Smoke live opt-in documentado
- [ ] PyInstaller build reproducible
- [ ] Checksum publicado
- [ ] Disclaimer visible en README y GUI
- [ ] Sin secretos en repo/logs/artefactos
