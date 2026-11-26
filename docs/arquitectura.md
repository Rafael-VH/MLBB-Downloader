# Arquitectura

## Principio

El proyecto usa **hexagonal-lite**: dominio puro + adaptadores concretos + casos de uso + shell CLI. La regla importante es la **dirección de dependencias**, verificada por test.

No se usa Clean Architecture completa (sin contenedor DI, sin puertos por cada clase, sin capas ceremoniales). En Python, la inyección es un parámetro; la verificación es un test de imports.

## Regla de dependencias

```text
domain  <-  adapters  <-  usecases  <-  cli
```

- `domain/`: Python puro. Sin HTTP, sin CLI, sin IO de filesystem, sin imports a adaptadores/usecases.
- `adapters/`: implementaciones concretas (httpx, filesystem, manifest persistence).
- `usecases/`: orquestación de sync/check/report; depende de dominio y de tipos concretos/adaptadores según el código actual.
- `cli.py`: shell Typer; parsea args, construye dependencias, imprime salida.

Guardrail: `tests/test_architecture.py` falla si `domain/*.py` importa módulos prohibidos o contiene hints de escritura.

## Estructura actual

```text
src/mlbb_downloader/
  __init__.py
  cli.py
  config.py
  errors.py
  reporting.py       # export JSON/Markdown de reportes
  domain/
    __init__.py
    images.py        # extracción/normalización de ImageAsset (puro)
    keying.py        # item_key, image_key, canonical_image_url, hero_identity
    layout.py        # sanitize_component
    manifest.py      # Manifest, ManifestItem (pydantic, validación)
    registry.py      # EndpointSpec catálogo
  adapters/
    __init__.py
    arena.py         # ArenaClient httpx, retry, paginación, get_bytes
    fsstore.py       # DataStore, escritura atómica JSON/bytes, hashing
    manifest_store.py# carga/guardado atómico del manifest
    paths.py         # resolución de rutas y contención en root
    progress.py      # checkpoint atómico _progress.json
  usecases/
    __init__.py
    engine.py        # sync/check genérico para artifacts JSON
    heroes.py        # dominio heroes sobre engine
    academy.py       # dominio academy sobre engine
    addon.py         # llamadas one-shot
    images.py        # sync/check de imágenes desde JSON locales
  gui/
    __init__.py
    app.py           # entrypoint PySide6
    main_window.py   # ventana principal, polling progreso
    workers.py       # QRunnable + señales
```

## Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Un solo engine JSON genérico | Evita duplicar resume/check/report por dominio |
| Imágenes como caso de uso separado | Fuente = bytes por URL, no endpoint JSON paginado |
| Manifest con pydantic | Validación simple y compatibilidad v1/v2 |
| Sin DI container | Sobrecosto en Python; parámetros/defaults bastan |
| Sin ABC por clase | Solo agregar Protocol si aparece un segundo implementador real |
| `domain` permite pydantic | Validación sin IO; prohibido httpx/typer/adapters/usecases/writes |

## Flujo de datos

### Sync JSON

```text
CLI -> usecase.sync_* -> engine.sync_many
     -> ArenaClient.get_paged
     -> DataStore.save_json (atomic .part + replace)
     -> ManifestStore.save (atomic)
```

### Check JSON

```text
CLI -> usecase.check_* -> engine.check_*
     -> ArenaClient.get_paged
     -> compara hash remoto vs manifest
     -> rehashea bytes locales para detectar corrupción
```

### Sync imágenes

```text
CLI -> usecases.images.sync_images
     -> collect_image_assets (lee JSON locales)
     -> domain.images extrae ImageAsset
     -> ArenaClient.get_bytes
     -> DataStore.save_bytes (atomic)
     -> ManifestStore.save
```

## GUI (MVP)

- GUI es otro shell sobre `usecases`, sin reescritura de lógica.
- `QThreadPool` + `QRunnable`/señales ejecutan sync/check fuera del hilo UI.
- Progreso: `_progress.json` atómico escrito por usecases/engine; GUI hace polling.
- Cancelación cooperativa: `JobCancelledError` + `threading.Event` pasado a engine/usecases.
- PyInstaller: spec base en `packaging/mlbb-downloader.spec`; app data en directorio de usuario.
