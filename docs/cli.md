# CLI

Entrada: `mlbb = mlbb_downloader.cli:app` (Typer).

## Comandos

### Globales

| Comando | Descripción |
|---|---|
| `mlbb sync` | Descarga todo lo público: heroes + academy + imágenes |
| `mlbb check` | Verifica todo lo público sin escribir |
| `mlbb status` | Muestra estado local del manifest/output |

### Heroes

| Comando | Descripción |
|---|---|
| `mlbb heroes sync` | Descarga heroes JSON; `--images` agrega imágenes |
| `mlbb heroes check` | Compara remoto vs local (`--hero-id` opcional) |

Opciones: `--output/-o`, `--limit`, `--force`, `--images` (sync), `--base-url`, `--delay`.

### Academy

| Comando | Descripción |
|---|---|
| `mlbb academy sync` | Descarga academy; `--images` agrega imágenes |
| `mlbb academy check` | Compara remoto vs local |

Opciones: `--output/-o`, `--limit`, `--force`, `--images` (sync), `--base-url`, `--delay`.

### Images

| Comando | Descripción |
|---|---|
| `mlbb images sync` | Descarga imágenes descubiertas en JSON locales |
| `mlbb images check` | Verifica integridad local; con `--local-only` no descarga remoto |

Opciones: `--output/-o`, `--force` (sync), `--local-only` (check), `--base-url`, `--delay`.

### Addon

| Comando | Descripción |
|---|---|
| `mlbb addon win-rate --match-now --wr-now --wr-future` | Calculadora de win rate |
| `mlbb addon ip` | Ubicación por IP según API |

## Comportamiento

- **Errores API**: se muestran como `error: <mensaje>` y exit code 1; sin traceback por defecto.
- **Exit code**: 1 si hay fallos en sync/check.
- **Resume**: sync salta artifacts existentes salvo `--force`.
- **Imágenes**: dependen de JSON ya presentes en el store.
- **Check**: reporta `unchanged/changed/new/missing/corrupted/not_downloaded/failed`.

## Mejoras CLI pendientes

- `--name <name>` para heroes (hoy existe `--hero-id`).
- `images check --local-only` (rehash disco, sin fetch remoto).
- `sync --report json|md` o `--report-file`.
- `--verbose/--quiet` y salida JSON machine-readable.
- Progreso en vivo (útil también para GUI/logs).
