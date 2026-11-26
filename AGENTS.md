# AGENTS.md — MLBB Downloader

Guía corta para agentes que trabajen en este repositorio. El plan detallado y la documentación viven en `docs/`.

## Qué es este proyecto

CLI Python (GUI diferida) que descarga datos de Mobile Legends: Bang Bang desde la Rone Arena API, con resume, verificación por hash, detección de cambios/faltantes/corrupción e imágenes.

- **Repositorio**: `mlbb-downloader-gui` (consumo de API pública; no modifica `rone-arena-api`).
- **Rama activa**: `feat/academy-addon`.
- **Estado**: CLI maduro; GUI/empaquetado pendientes.

## Dónde leer antes de tocar código

1. `docs/README.md` — índice de documentación.
2. `docs/plan-maestro.md` — estado actual, brechas y roadmap vigente.
3. `docs/arquitectura.md` — reglas de dependencia y estructura.
4. `docs/cobertura-api.md` — endpoints, políticas y pendientes.
5. `docs/plan-original.md` — spec/plan inicial extraído de este archivo.

## Fuente de verdad

- API base: `https://arena.rone.dev/api`
- OpenAPI: `https://arena.rone.dev/api/openapi.json`
- No hardcodear supuestos cuando el schema/OpenAPI pueda leerse.

## Reglas de trabajo

- **CLI primero**; GUI es fase final.
- **Commits por work unit** en rama de feature autorizados; **push solo con decisión del usuario**. No commitear cambios ajenos.
- **Idempotencia**: todo downloader/sync debe poder reanudarse sin corromper datos.
- **No bloquear UI** cuando exista GUI: HTTP en workers/hilos, nunca en hilo principal.
- **Cambios pequeños y revisables**. No agregar dependencias sin justificación.
- **Tests**: todo endpoint/tool nuevo debe tener entrada de manifest, regla de ruta, soporte check-update y cobertura de tests. `uv run pytest` y `uv run ruff check .` antes de cerrar.
- **Esports**: diferido/no prioritario por decisión del usuario. No ampliar alcance sin pedido explícito.

## Seguridad / legal

- No embeber secretos, claves privadas ni JWTs. Nunca loguear tokens.
- Tokens de usuario solo opt-in; storage seguro (keyring/almacenado cifrado); nunca en “Download All” por defecto.
- Respetar rate limits/WAF: secuencial, retries acotados, backoff en 403/405/429/5xx. Delay configurable, default seguro `>= 0.35s`.
- Disclaimer visible en README/GUI About: proyecto no oficial, no afiliado a Moonton. Marcas/assets pertenecen a sus dueños.

## Arquitectura (resumen)

Hexagonal-lite: `domain/` puro ← `adapters/` ← `usecases/` ← `cli.py`. La regla de dependencias se verifica con `tests/test_architecture.py`. Ver `docs/arquitectura.md`.
