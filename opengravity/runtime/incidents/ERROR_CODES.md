# Catálogo de códigos de incidencia (validador)

| error_code | Dominio | Descripción | Acción sugerida |
|------------|---------|-------------|-----------------|
| `FOLDER_MISSING` | io | Carpeta de entregables no existe | Verificar ruta en `state.json` o `--engineering-folder` |
| `FILE_MISSING` | io | Archivo esperado no encontrado | Comprobar nombre, regenerar entregable |
| `FILE_EMPTY` | io | Archivo existe pero está vacío | Regenerar; revisar permisos o bloqueo |
| `PDF_MEMORIA_MISSING` | engineering | Falta PDF memoria del estudio | Copiar PDF con nombre ASCII-safe si hay acentos |
| `PDF_ANNOTATED_MISSING` | engineering | Falta PDF anotado COM | Ejecutar script de anotación; limitar páginas si PDF muy grande |
| `XLSX_RCC_MISSING` | engineering | Falta Excel RCC / hoja revisión | Regenerar RCC; evitar escribir en celdas fusionadas |
| `DELIVERABLES_EXPECTED_EMPTY` | ledger | `deliverables.expected` vacío | Completar DoD en `state.json` antes de validar |
| `DELIVERABLES_PRODUCED_EMPTY` | ledger | `deliverables.produced` vacío | Registrar rutas absolutas de salidas |
| `DELIVERABLE_PATH_INVALID` | ledger | Ruta de entregable no es archivo válido | Usar rutas absolutas Windows |
| `TESTS_RUN_EMPTY` | software | Sin registro de tests ejecutados | Documentar comando y resultado en `tests_run` |
| `STATE_INVALID` | ledger | `state.json` ilegible o incompleto | Reparar JSON; usar plantilla `_TEMPLATE` |
| `VALIDATION_PASSED` | meta | Validación exitosa | Ninguna acción requerida |
| `GEO_NO_OVERLAP` | geo | Emplazamiento fuera de ortofoto | Verificar KMZ/GeoTIFF y manifest WGS84 |
| `GEO_SITE_OUTSIDE_ORTHO` | geo | Cobertura ortofoto insuficiente | Ampliar vuelo o cambiar ortofoto de referencia |
| `GEO_PARTIAL_OVERLAP_WARN` | geo | Solapamiento parcial | Revisar bbox en `opengravity/runtime/geo/` |
| `GEO_SITE_INSIDE_ORTHO` | geo | Emplazamiento dentro de ortofoto | OK |
