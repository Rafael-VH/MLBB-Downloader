# Cobertura API

Fuente: `https://arena.rone.dev/api` + comportamiento observado en vivo. Esports diferido por decisión del usuario.

## Heroes

| Endpoint | Estado | Notas |
|---|---|---|
| `GET /heroes` | ✅ | index JSON, paginado |
| `GET /heroes/{id}` | ✅ | detail |
| `GET /heroes/{id}/stats` | ✅ | stats |
| `GET /heroes/{id}/skill-combos` | ✅ | subrecurso |
| `GET /heroes/{id}/trends` | ✅ | subrecurso |
| `GET /heroes/{id}/relations` | ✅ | subrecurso |
| `GET /heroes/{id}/counters` | ✅ | subrecurso |
| `GET /heroes/{id}/compatibility` | ✅ | subrecurso |
| `GET /heroes/{id}/wallpapers` | ✅ | JSON + descarga de imágenes |
| `GET /heroes/rank` | ✅ | colección; `optional` (upstream puede fallar transitoriamente) |
| `GET /heroes/positions` | ✅ | colección |
| `GET /heroes/wallpapers` | ✅ | galería global JSON |

## Academy

| Endpoint / grupo | Estado | Política |
|---|---|---|
| `meta/version` | ✅ | colección |
| `heroes/catalog` | ✅ | colección; fuente para imágenes catalog |
| `roles` | ✅ | colección |
| `equipment` | ✅ | colección |
| `equipment/expanded` | ✅ | colección |
| `spells` | ✅ | colección |
| `emblems` | ✅ | colección |
| `ranks` | ✅ | colección; cubre rangos 1..9999 |
| `heroes` (filter) | ✅ | sin filtros masivos, catálogo base |
| `heroes/{id}/stats` | ✅ | per-hero |
| `heroes/{id}/lane` | ✅ | per-hero; fuente de lanes reales |
| `heroes/{id}/win-rate/timeline` | ✅ | solo lanes que el héroe juega |
| `heroes/{id}/builds` | ✅ | solo lanes que el héroe juega |
| `heroes/{id}/counters` | ✅ | per-hero |
| `heroes/{id}/teammates` | ✅ | per-hero (path live `/teammates`) |
| `heroes/{id}/trends` | ✅ | per-hero |
| `recommended` | ⚠️ excluido | UGC masivo; 10000 records; detalle redundante |
| `heroes/{id}/recommended` | ⚠️ excluido | UGC por héroe |
| `ranks/{rank_id}` | ⚠️ excluido | redundante con `/ranks` |
| `heroes/ratings` | ⚠️ unavailable | HTTP 200 + `code 10407` |
| `heroes/ratings/{subject}` | ⚠️ unavailable | ratings offline |

## Addon

| Endpoint | Estado | Notas |
|---|---|---|
| `win-rate-calculator` | ✅ | interactivo CLI, no bulk |
| `ip` | ✅ | interactivo CLI, no bulk |

## Esports

| Área | Estado | Notas |
|---|---|---|
| leagues, matches, teams, stats, extras, simulator | ⏸️ diferido | decisión explícita del usuario: innecesario por ahora |

## User/Auth

| Área | Estado | Notas |
|---|---|---|
| login/info/stats/matches/friends/etc. | ❌ pendiente | opt-in explícito; nunca en “Download All” por defecto; sin tokens en logs |

## Brechas de cobertura detectadas

1. **Validación automática contra OpenAPI**: no hay script de verificación/generación; riesgo de deriva.
2. **Cobertura de imágenes**: dirigida por campos conocidos; galería global y nuevos campos requieren extender `domain/images.py` con tests.
