# Documentación — MLBB Downloader

Esta carpeta concentra los planes de implementación y la documentación técnica del proyecto.

## Índice

| Documento | Propósito |
|---|---|
| [plan-maestro.md](plan-maestro.md) | Estado actual, brechas, roadmap y criterios de aceptación |
| [plan-original.md](plan-original.md) | Spec/plan inicial extraído de `AGENTS.md` (referencia histórica) |
| [arquitectura.md](arquitectura.md) | Arquitectura hexagonal-lite, reglas de dependencia y estructura |
| [cobertura-api.md](cobertura-api.md) | Cobertura de endpoints Rone Arena API, políticas y pendientes |
| [modelo-datos.md](modelo-datos.md) | Manifest v2, layout de salida, hashing, resume y corrupción |
| [cli.md](cli.md) | Comandos CLI, opciones, comportamiento y salidas |
| [calidad-release.md](calidad-release.md) | Tests, lint, CI, empaquetado, release y checklist legal |

## Estado rápido

- **Rama**: `feat/academy-addon`
- **Stack**: Python 3.14 + uv + httpx + pydantic v2 + typer + PySide6 + pytest + ruff
- **Tests**: 91 passed, ruff clean
- **Fase actual**: CLI maduro + GUI MVP PySide6; packaging/CI con base implementada, pendiente validación en limpio/CI real

## Fuente de verdad

- `AGENTS.md`
- `https://arena.rone.dev/api/openapi.json`
- Código en `src/mlbb_downloader/`
- Tests en `tests/`
