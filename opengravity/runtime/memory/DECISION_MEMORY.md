# Decision Memory — Sentido común técnico (Valle + Sax)

> Vista consolidada para `@files` en Cursor. Índice machine-readable: `index.json` · Lecciones detalladas: subcarpetas `engineering/`, `excel/`, `pdf/`, `webodm/`.

---

## Reglas de oro (aplicar siempre)

1. **Rutas absolutas** en `deliverables.produced` — nunca relativas al repo si los entregables viven en `Proyectos/`.
2. **Nombres ASCII-safe** al ingestar (`SAX_MEMORIA_0F.pdf`, `SAX_RRCC_COMENTADO.xlsx`) — evita fallos cp1252/UTF-8.
3. **Excel RCC:** no escribir en celdas fusionadas (MergedCell) — mapear C3, C7 u otras celdas libres antes de openpyxl.
4. **PDF anotado:** anotar solo páginas ancla por COM — memorias >100 pp generan PDFs enormes o bloqueos.
5. **Salida PDF única:** nombre con fecha (`*_COM_REV03_12072026.pdf`) — no sobrescribir con visor abierto.
6. **Validar antes de cerrar:** `validate_deliverables.py` + `cross_validate.py` si hay `geo_link`.
7. **Git cleanup ≠ borrar entregables:** tras stash/reset, revalidar que rutas en `state.json` siguen en disco.

---

## Colectora Valle (PROT-VALLE-0B-REV03)

| Tema | Lección |
|------|---------|
| Veredicto | REC global — 67N L14, E79=Y, HEPRZ1/Group2, impedancias no unificadas |
| Excel Rev.03 | Clonar RCC original; escribir solo celdas no fusionadas |
| PDF COM | Evidencias en pp. 49, 52, Tabla 14 — anotación selectiva |
| Geo | Manifest `colectora_valle.geo.json` + KMZ febrero 2026 en `geo_link` |
| Entregables | Excel Rev03 Propiedad + PDF anotado + `REVISION_Propiedad_Valle_0B_Rev03.md` |

**MEM vinculadas:** MEM-001 (Excel), MEM-002 (PDF), MEM-004 (rutas)

---

## Nudo Sax (PROT-SAX-0F-OMEXOM)

| Tema | Lección |
|------|---------|
| RCC | Extraer COM con regex tolerante a multilínea; columna C4 = página ancla memoria |
| Veredicto | REC — COM abiertos (67N, 68 sin nota, FAT AT1, etc.) |
| Insumos | Copiar PDF/Excel a nombres ASCII antes de procesar |
| Anotación PDF | Ancla por rango de páginas del RCC, no todas las páginas |
| Geo | Manifest `nudo_sax.geo.json` — completar `orthophoto_file` tras export WebODM |

**MEM vinculadas:** MEM-003 (ASCII), MEM-002 (PDF), MEM-005 (cross-geo)

---

## WebODM + cross-validación

- Docker + NodeODM obligatorio para ortofotos.
- **Preset recomendado:** `ortofoto_ingenieria` → `python scripts/webodm_preset.py --preset ortofoto_ingenieria --api`
- Nodo con GPS drone: preferir `sfm-algorithm=triangulation` (incluido en preset).
- Resolución ortofoto ingeniería: **2 cm/px** (preset); DSM activado para contexto 3D.
- Exportar → verificar tamaño (>1 MB) → `cross_validate.py` → limpiar proyecto.
- Token API en `webodm/.webodm_token`.

**MEM vinculada:** MEM-005

---

## Self-healing (orden de intento)

```
1. Buscar error_code en este archivo / index.json
2. Aplicar acción sugerida en incidents.json
3. Re-ejecutar script generador (no parche manual en chat)
4. Revalidar
5. Si OK → promover a lección (--from-incident)
6. Si falla 2× → HITL
```

---

## Códigos de error frecuentes

| Código | Acción rápida |
|--------|---------------|
| `FILE_MISSING` | Regenerar entregable; comprobar ruta absoluta post-cleanup |
| `XLSX_RCC_MISSING` | Regenerar RCC; evitar merged cells |
| `PDF_ANNOTATED_MISSING` | Script anotación; limitar páginas |
| `PDF_MEMORIA_MISSING` | Copia ASCII-safe del PDF memoria |
| `GEO_NO_OVERLAP` | Revisar manifest WGS84 vs KMZ/GeoTIFF |
| `DELIVERABLE_PATH_INVALID` | Solo rutas absolutas Windows |

Catálogo completo: `../incidents/ERROR_CODES.md`

---

*Actualizar tras cada incidencia resuelta. No volcar chats — 1 lección = 1 problema verificado.*
