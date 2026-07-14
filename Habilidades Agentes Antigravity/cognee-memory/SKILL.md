# SKILL: Cognee Memory Agent

## Descripción
Este agente utiliza la librería `cognee` para proporcionar una capa de memoria persistente y estructurada mediante Grafos de Conocimiento. Su objetivo es reducir alucinaciones y permitir que el Agente Maestro acceda a hechos verificados y relaciones complejas entre documentos y conversaciones pasadas.

## Capacidades
- **Ingesta ECL (Extract, Cognify, Load)**: Procesa información no estructurada y la convierte en nodos de conocimiento.
- **Búsqueda Semántica y en Grafo**: Recupera información no solo por similitud vectorial, sino por relaciones lógicas.
- **Reducción de Alucinaciones**: Sirve como fuente de verdad (Source of Truth) para el orquestador.

## Instrucciones de Uso (para el Orquestador)
1. Usa este agente cuando el usuario mencione información que debe ser "recordada para siempre" o cuando necesites consultar datos históricos complejos.
2. Para guardar información: "Envía [datos] al agente cognee para que los procese (add/cognify)".
3. Para recuperar información: "Busca en el agente cognee sobre [tema]".

## Configuración Técnica
- Requiere Python 3.10+
- `pip install cognee`
- Variable de entorno `LLM_API_KEY` o `.env` configurado.
