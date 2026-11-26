# Modelo de datos

## Manifest v2

Archivo: `manifest.json` en el root de salida.

### Campos

```json
{
  "schema_version": 2,
  "base_url": "https://arena.rone.dev/api",
  "generated_at": "2026-...",
  "items": {
    "<key>": {
      "endpoint": "/heroes/1",
      "params": {"hero_id": 1},
      "path": "heroes/Miya/detail.json",
      "sha256": "...",
      "size": 1234,
      "downloaded_at": "2026-...",
      "total": 1,
      "kind": "json",
      "source_url": null,
      "content_type": null
    }
  }
}
```

### Claves

- **JSON**: `item_key(endpoint, params)` — endpoint + query params ordenados.
- **Imagen**: `image::canonical_url` — URL canónica de origen; `wsrv.nl/?url=` se desenvuelve para identidad.

### Compatibilidad

- Lee manifiestos v1.
- Escribe manifiestos v2.
- Campos nuevos son opcionales con defaults.

## Layout de salida

```text
data/
  manifest.json
  heroes/
    index.json
    <Hero>/
      detail.json
      stats.json
      skill-combos.json
      trends.json
      relations.json
      counters.json
      compatibility.json
      wallpapers.json
      images/
        head.png
        painting.png
        skills/<id>-<name>.png
      wallpapers/
        <skin>-<resolution>.jpg
  academy/
    version.json
    roles.json
    equipment.json
    equipment-expanded.json
    spells.json
    emblems.json
    ranks.json
    heroes/
      catalog.json
      filter.json
      <Hero>/
        lane.json
        stats.json
        counters.json
        teammates.json
        trends.json
        builds-<lane>.json
        win-rate-<lane>.json
    catalog/<Hero>/images/
      head.jpg
      head_big.jpg
      painting.webp
```

## Integridad y resume

| Mecanismo | Comportamiento |
|---|---|
| Escritura atómica | `.part` + `os.replace` |
| Hash | SHA-256 de bytes guardados |
| Resume | si key existe en manifest y archivo presente, sync salta (salvo `--force`) |
| Manifest corrupto | se cuarentena a `manifest.json.corrupt-*`, no aborta corrida |
| Check remoto | compara hash remoto vs manifest |
| Check local | rehashea bytes en disco; si difiere del manifest → `corrupted` |

## Formato JSON almacenado

Los artifacts JSON se guardan como:

```json
{
  "endpoint": "/heroes/1",
  "total": 1,
  "records": [ ... ]
}
```

No se modelan payloads de upstream con pydantic: las formas varían entre list/detail.

## Pendientes de modelo

- `_progress.json` por job para GUI/cancel-resume fino.
- Export de reportes (`.json`/`.md`) por corrida.
- Modelo de credenciales/auth para dominio user (nunca en manifest público).
