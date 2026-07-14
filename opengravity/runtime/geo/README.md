# Geo manifests (Fase 4)

Manifiestos WGS84 para validacion cruzada ingenieria ↔ ortofoto.

Convencion en `state.json`:

```json
"geo_link": {
  "manifest": "opengravity/runtime/geo/colectora_valle.geo.json",
  "orthophoto_file": "G:/ruta/ortofoto.kmz"
}
```

Validar:

```bash
python scripts/cross_validate.py --state opengravity/runtime/tasks/<id>/state.json
python scripts/cross_validate.py --geo opengravity/runtime/geo/colectora_valle.geo.json --ortho-kmz "G:/.../ortofoto.kmz"
```

Fuentes de bbox ortofoto soportadas: `.kmz`, `.kml`, `.geo.json`, `.tif`/`.tiff` (requiere rasterio).
