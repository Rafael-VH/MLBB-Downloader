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
| `GET /heroes/rank` | ❌ | pendiente |
| `GET /heroes/positions` | ❌ | pendiente |
| `GET /heroes/wallpapers` | ❌ | galería global pendiente |

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

1. **Registry incompleto para heroes**: `domain/registry.py` declara `HEROES_INDEX` y `HERO_STATS`, pero la implementación real soporta más subrecursos. Faltan también rank/positions/wallpapers gallery.
2. **No hay validación automática contra OpenAPI**: riesgo de deriva.
3. **Cobertura de imágenes**: dirigida por campos conocidos; si la API agrega campos, hay que extender `domain/images.py` con tests.
