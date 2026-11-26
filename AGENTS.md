# Plan detallado — GUI Python (MLBB Downloader)

Creé el documento base para el nuevo proyecto en `docs/gui-downloader/AGENTS.md`. Abajo va el plan detallado, alineado con la API real del repo.

## 1. Objetivo y alcance

- **App de escritorio en Python** con GUI para exponer herramientas basadas en la API de Rone Arena.
- **Descarga completa** de información pública de MLBB: héroes, academy, esports, addon; `user` solo con autenticación explícita.
- **Botones clave**: `Descargar todo`, `Comprobar actualizaciones`, `Descargar categoría`, `Descargar seleccionado`, `Reintentar fallidos`, `Pausar/Reanudar`, `Abrir carpeta`.
- **Detección** de archivos faltantes, descargas incompletas y cambios/actualizaciones remotas.
- **Ejecutable** Windows (`.exe`) con PyInstaller; base preparada para CI/release en GitHub.

## 2. Base técnica (repositorio nuevo)

- **Stack recomendado**: Python 3.12+, PySide6, `httpx`, `pydantic` v2, `pytest`, `ruff`, `uv`, PyInstaller.
- **Estructura**: `src/mlbb_downloader/{api,downloaders,storage,services,ui,utils}`, `tests/`, `.github/workflows/`.
- **Config local**: `%APPDATA%/MLBBDownloader/` (config, logs, cache); datos descargados en carpeta elegida por el usuario.
- **Referencia existente**: `scripts/fetch_hero_assets.py` ya resuelve héroes, wallpapers, checkpoint (`_progress.json`), reintentos y nombres seguros; la GUI debe generalizar ese patrón.

## 3. Mapa de herramientas por API

| Categoría | Endpoints/herramientas | Salida | Auth |
| --- | --- | --- | --- |
| Heroes | `/heroes`, `/heroes/rank`, `/heroes/positions`, `/heroes/{id}`, `/stats`, `/skill-combos`, `/trends`, `/relations`, `/counters`, `/compatibility`, `/wallpapers`, `/heroes/{id}/wallpapers` | JSON + MD + imágenes (icon, splash, skills, wallpapers desktop/mobile) | No |
| Academy | `/academy/meta/version`, `heroes/catalog`, `roles`, `equipment`, `equipment/expanded`, `spells`, `emblems`, `ranks`, `ranks/{id}`, `recommended`, builds/lane/rating/timeline/matchups/stats según OpenAPI | JSON por endpoint, índices MD, assets si aplica | No |
| Esports | `id/ph/my/kh`: schedule, playoffs, standings, matches, teams, team, statistics; extras por liga (hero-pools/player-pools/mvp/savage-maniac/images/player) | JSON por liga/entidad, reportes MD | No |
| Addon | `win-rate-calculator`, `ip` | Herramienta interactiva (no bulk) | No |
| User | `auth/send-vc`, `login`, `logout`, `info`, `stats`, `privacy/settings`, `season`, `matches`, `matches/{id}`, `heroes/frequent`, `matches/hero/{id}`, `friends` | JSON privado separado | Sí, opt-in |

**Regla**: el catálogo de endpoints se genera/valida desde `GET /api/openapi.json` para no quedar obsoleto.

## 4. Modelo de descarga y almacenamiento

```text
<output>/
  manifest.json
  reports/
    last-check.json
    last-download.md
  heroes/
    index.json
    Miya/
      hero.md
      detail.json
      stats.json
      icon.png
      splash.jpg
      skill-00-passive.png
      wallpaper-desktop-01-*.jpg
  academy/
  esports/
    id/
    ph/
    my/
    kh/
  addon/
  user/            # solo opt-in
```

- **Manifest**: por ítem guarda endpoint, URL origen, ruta local, tamaño, `sha256`, `etag`/`last-modified` si existe, fecha, estado.
- **Escritura segura**: descargar a `.part`, verificar, luego renombrar; manifest con escritura atómica.
- **Idempotencia**: re-ejecutar no duplica ni corrompe; omite lo ya válido.

## 5. Comprobar actualizaciones / faltantes

Botón `Comprobar actualizaciones` (dry-run):

1. Cargar `manifest.json`.
2. Consultar remoto (listas, totales, IDs, versión de juego/patch donde aplique).
3. Comparar:
  - **Faltante**: archivo en manifest no existe, o entidad remota sin archivo local.
  - **Nuevo**: héroe/partido/equipo/rank/ítem no visto antes.
  - **Cambiado**: hash distinto, ETag/Last-Modified distinto, o campos clave cambiados.
  - **Sin cambios**: coincide hash/metadatos.
4. Generar reporte con conteos y acciones sugeridas; no descargar salvo confirmación.

Señales útiles: `academy/meta/version` (`game_version`), totales de catálogos, conteo de héroes, IDs nuevos, archivos con tamaño 0.

## 6. Diseño GUI

- **Sidebar**: Dashboard, Héroes, Academy, Esports, Addon, User, Configuración, Logs.
- **Barra superior**: Base URL, carpeta salida, `Comprobar actualizaciones`, `Descargar todo`, `Pausar/Reanudar`, `Cancelar`.
- **Dashboard**: total descargado, faltantes, actualizaciones, último sync, uso de disco, errores.
- **Vista por categoría**: tabla/cards con estado, último run, nuevos/cambiados/faltantes, acciones por fila.
- **Log panel**: nivel, timestamp, endpoint, resultado; exportar log.
- **Workers**: QThread/QRunnable; nunca bloquear UI; progreso por señal.

## 7. Seguridad, resiliencia y cumplimiento

- **Rate limit/WAF**: requests secuenciales por defecto, delay configurable (>=0.35s), retries acotados con backoff en 403/405/429/5xx; rotación suave de User-Agent solo si es necesario.
- **Auth**: JWT/token nunca en logs; guardado opt-in en keyring; datos de usuario en carpeta separada.
- **Legal**: disclaimer visible (no afiliado a Moonton), atribución de fuentes, no redistribuir secretos.
- **Robustez**: cancelar limpio, reanudar, reporte de fallidos, validación de JSON/schema.

## 8. Empaquetado como ejecutable

- PyInstaller `--windowed --onefile --name MLBBDownloader`.
- Incluir assets Qt; probar en Windows limpio sin Python.
- Config/logs en AppData, no junto al exe.
- GitHub Actions: `ci.yml` (ruff, pytest, build smoke), `release.yml` (tag `v*`, build exe, checksums, GitHub Release).

## 9. Roadmap por hitos

1. **Fundación**: scaffold, config, cliente HTTP, manifest, logging, CLI básica.
2. **MVP Héroes**: catálogo + detalle + assets + wallpapers + check updates + resume.
3. **Academy/Addon**: registry OpenAPI, descargas por endpoint, herramientas interactivas.
4. **Esports**: 4 ligas, matches/teams/stats, imágenes proxy.
5. **User opt-in**: flujo auth, almacenamiento privado, exclusión por defecto.
6. **GUI final + empaquetado**: dashboard, pausa/cancelar, PyInstaller, release.

## 10. Criterios de aceptación

- `Descargar todo` completa dataset público sin corromper archivos.
- `Comprobar actualizaciones` reporta nuevos/cambiados/faltantes sin descargar.
- Reanudación funciona tras corte/interrupción.
- No hay secretos en logs ni en repo.
- `.exe` funciona en Windows limpio.
- README/AGENTS incluyen uso, límites, disclaimer y atribución.

## 11. Insumos inspeccionados

- `scripts/fetch_hero_assets.py` (patrón de descarga, retries, checkpoint, wallpapers).
- `src/app/api/routers/{heroes,academy,esports,addon,user,root}.py` (superficie de endpoints).
- `README.md`, `pyproject.toml`, `.env.example` (contexto del proyecto y URLs).