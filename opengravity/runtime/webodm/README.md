# WebODM — configuración Antigravity

## Archivos

| Archivo | Uso |
|---------|-----|
| `node_options_schema.json` | Catálogo completo de opciones del nodo (referencia) |
| `presets/ortofoto_ingenieria.json` | Preset recomendado: ortofoto + DSM para superposición con planos |
| `presets/ortofoto_rapida.json` | Preset rápido: solo ortofoto, menos cómputo |

## Aplicar preset en WebODM UI

Al crear tarea → **Options** → pegar JSON generado:

```bash
python scripts/webodm_preset.py --preset ortofoto_ingenieria
```

Copia la salida en el campo de opciones de la tarea.

## API WebODM

```bash
python scripts/webodm_preset.py --preset ortofoto_ingenieria --api
```

Devuelve array `[{"name":"...","value":"..."}]` listo para POST `/api/projects/{id}/tasks/`.

## Token

1. Copiar `scripts/webodm.local.example.json` → `scripts/webodm.local.json` (usuario/contraseña).
2. Ejecutar:
   ```bash
   python scripts/webodm_get_token.py --test
   ```
   o doble clic: `webodm/Obtener Token WebODM.bat`

Token guardado en `webodm/.webodm_token` (caduca ~6 h; usar `--force` para renovar).
