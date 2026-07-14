import cognee
import asyncio
import os
import sys

# Configuración: Asegúrate de tener LLM_API_KEY en tu .env o entorno
# os.environ["LLM_API_KEY"] = "TU_KEY"

async def add_knowledge(text):
    """Añade texto a la base de conocimiento de Cognee"""
    print(f"📦 Añadiendo conocimiento: {text[:50]}...")
    await cognee.add(text)
    await cognee.cognify()
    print("✅ Conocimiento procesado e indexado en el Grafo.")

async def search_knowledge(query):
    """Busca en el grafo de conocimiento"""
    print(f"🔍 Buscando: '{query}'")
    results = await cognee.search(query)
    if not results:
        print("❌ No se encontraron resultados relacionados.")
        return
    
    print("\n--- Resultados de Cognee ---")
    for result in results:
        print(result)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python cognee_bridge.py [add|search] \"mensaje\"")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    content = sys.argv[2]
    
    if action == 'add':
        asyncio.run(add_knowledge(content))
    elif action == 'search':
        asyncio.run(search_knowledge(content))
    else:
        print(f"Acción desconocida: {action}")
