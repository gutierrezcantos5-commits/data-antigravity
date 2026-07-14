---
id: MEM-005
domain: webodm
profile: engineering
error_codes: [GEO_NO_OVERLAP, GEO_SITE_OUTSIDE_ORTHO]
task_id: TEMPLATE
created_at: 2026-07-13
title: Enlazar geo manifest antes de validar ortofoto
---

## Problema

Revision de protecciones sin comprobar si la ortofoto cubre el emplazamiento real.

## Causa raiz

Ingenieria (RCC/PDF) y geoespacial (WebODM/KMZ) en silos sin bbox WGS84 compartido.

## Resolucion

- Crear manifiesto en `opengravity/runtime/geo/<proyecto>.geo.json` con `site_bbox_wgs84`.
- En `state.json` anadir `geo_link.manifest` y `geo_link.orthophoto_file`.
- Ejecutar `python scripts/cross_validate.py --state ...` antes de cerrar la tarea.

## Evitar en el futuro

- Preflight + cross_validate en proyectos con componente campo/dron.
- Alerta roja si overlap_ratio_site < 20%.

## Referencias

- `scripts/cross_validate.py`
- `opengravity/runtime/geo/README.md`
