from __future__ import annotations

import json
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_PATH = os.path.join(REPO_ROOT, "Habilidades Agentes Antigravity", "nexus_orchestrator.py")
COGNEE_PATH = os.path.join(REPO_ROOT, "Habilidades Agentes Antigravity", "cognee-memory", "cognee_bridge.py")
SKILLS_DIR = os.path.join(
    REPO_ROOT,
    "Habilidades Agentes Antigravity",
    "nuevas habilidades",
    "habilidades preferidas",
)

mcp = FastMCP("Antigravity Bridge")


def _run_python(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, script, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


@mcp.tool()
def list_engineering_calculators():
    """List available engineering calculators from NEXUS (Protections, cables, etc)."""
    result = _run_python(ORCHESTRATOR_PATH, "list")
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "orchestrator failed"}
    return json.loads(result.stdout)


@mcp.tool()
def run_engineering_calculation(calculator: str, params: str = "{}"):
    """Run an engineering calculation on NEXUS. Params should be a JSON string."""
    result = _run_python(ORCHESTRATOR_PATH, "calc", calculator, params)
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "calculation failed", "stdout": result.stdout}
    return json.loads(result.stdout)


@mcp.tool()
def search_global_skills(query: str):
    """Search for proven solutions in the Antigravity Awesome Skills repository (+860 skills)."""
    matches: list[str] = []
    if os.path.isdir(SKILLS_DIR):
        for item in os.listdir(SKILLS_DIR):
            if query.lower() in item.lower():
                matches.append(item)
    return {"found": matches[:10], "total": len(matches)}


@mcp.tool()
def memory_add(text: str):
    """Add long-term memory/knowledge to the Antigravity graph (Cognee)."""
    result = _run_python(COGNEE_PATH, "add", text)
    return result.stdout or result.stderr


@mcp.tool()
def memory_search(query: str):
    """Search long-term memory for related concepts or past projects."""
    result = _run_python(COGNEE_PATH, "search", query)
    return result.stdout or result.stderr


@mcp.tool()
def list_workspace_files(subdir: str = ""):
    """List files in the DATA Antigravity workspace to help with project management."""
    target_path = os.path.join(REPO_ROOT, subdir) if subdir else REPO_ROOT
    if not os.path.exists(target_path):
        return {"error": "Path not found", "path": target_path}
    files = os.listdir(target_path)
    return {"path": target_path, "files": files[:50], "total": len(files)}


@mcp.tool()
def fetch_url(url: str):
    """Fetch the text content of a URL (lightweight alternative to Browser)."""
    import requests

    try:
        response = requests.get(url, timeout=10)
        return {"status": response.status_code, "content": response.text[:5000]}
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    mcp.run()
