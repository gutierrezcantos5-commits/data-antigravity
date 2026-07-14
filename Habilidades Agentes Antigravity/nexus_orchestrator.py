#!/usr/bin/env python3
"""
Nexus Orchestrator - Script para integrar con Gemini
Permite ejecutar cálculos en NEXUS y enviar tareas al Agente Ingeniero
"""

import requests
import json
import sys

NEXUS_CALC_URL = "http://72.61.21.53:8504/"
AGENTE_ING_URL = "http://72.61.21.53:8502/"

CALCULATORS = {
    "protecciones": "Cálculo de protecciones (TC, relés)",
    "lat": "Líneas AT (flecha, tensión)",
    "fv": "Plantas solares FV",
    "ieee80": "Puesta a tierra IEEE 80",
    "barras": "Dimensionamiento barras",
    "ctvt": "CT/VT (burden)",
    "altitud": "Distancias altitud IEC",
    "cables": "Cables AT/MT",
    "conductores": "Conductores AT/MT",
    "aislamiento": "Aislamiento IEC 60071",
    "ssaa": "Servicios auxiliares",
    "ccc": "Cortocircuito IEC 60909"
}

def list_calculators():
    """Lista calculadoras disponibles"""
    return {"calculators": CALCULATORS, "count": len(CALCULATORS)}

def execute_calculation(calculator, params=None):
    """Ejecuta un cálculo en NEXUS"""
    if calculator not in CALCULATORS:
        return {"error": f"Calculadora '{calculator}' no encontrada"}
    
    # Por defecto, parámetros vacío
    if params is None:
        params = {}
    
    # Ejecutar en NEXUS (simulado - retorna info)
    return {
        "status": "ready",
        "calculator": calculator,
        "description": CALCULATORS[calculator],
        "params": params,
        "url": f"{NEXUS_CALC_URL}#calc-{calculator}",
        "note": "Abre esta URL en el navegador para ejecutar"
    }

def send_to_agent(task, files=None, normas=None):
    """Envía tarea al Agente Ingeniero"""
    # El agente NEXUS no tiene API, retorna URL para abrir
    return {
        "status": "ready",
        "agent_url": AGENTE_ING_URL,
        "task": task,
        "files": files or [],
        "normas": normas or [],
        "instruction": f"Abre {AGENTE_ING_URL} y envía esta tarea: {task}"
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps(list_calculators(), indent=2))
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "list":
        print(json.dumps(list_calculators(), indent=2))
    
    elif command == "calc":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Falta nombre de calculadora"}))
            sys.exit(1)
        calc = sys.argv[2]
        params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(execute_calculation(calc, params), indent=2))
    
    elif command == "agent":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Falta descripción de tarea"}))
            sys.exit(1)
        task = sys.argv[2]
        print(json.dumps(send_to_agent(task), indent=2))
    
    else:
        print(json.dumps({"error": "Comando desconocido"}))

if __name__ == "__main__":
    main()
