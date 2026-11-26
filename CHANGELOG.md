# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added
- Hexagonal-lite architecture (`domain/`, `adapters/`, `usecases/`, CLI).
- Heroes and academy sync/check with resumable manifest v2 and SHA-256 verification.
- Image discovery/sync/check with canonical URL dedupe and local-only integrity checks.
- Top-level `mlbb sync/check`, `--report` JSON/Markdown export, `_progress.json` checkpoints.
- PySide6 GUI MVP skeleton (`mlbb-gui`) with background workers and cooperative cancel.
- OpenAPI registry check script and registry consistency tests.

### Notes
- Esports endpoints are deferred by product decision.
- User/auth endpoints remain opt-in and are not implemented yet.
