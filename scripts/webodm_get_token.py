# -*- coding: utf-8 -*-
"""
Obtiene token JWT de WebODM y lo guarda en webodm/.webodm_token

Uso:
  python scripts/webodm_get_token.py
  python scripts/webodm_get_token.py --test
  python scripts/webodm_get_token.py --force
  python scripts/webodm_get_token.py --username admin --password secret

Requisito: copiar scripts/webodm.local.example.json -> scripts/webodm.local.json
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOKEN_PATH = os.path.join(REPO_ROOT, "webodm", ".webodm_token")
LOCAL_CONFIG = os.path.join(REPO_ROOT, "scripts", "webodm.local.json")
DEFAULT_CONFIG = os.path.join(REPO_ROOT, "scripts", "webodm.config.json")


def _resolve_local_config() -> str | None:
    for rel in ("scripts/webodm.local.json", "webodm/webodm.local.json"):
        path = os.path.join(REPO_ROOT, rel.replace("/", os.sep))
        if os.path.isfile(path):
            return path
    return None


def _load_config() -> dict:
    local = _resolve_local_config()
    path = local or DEFAULT_CONFIG
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "No hay config. Crea scripts/webodm.local.json o webodm/webodm.local.json"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_token(url: str, username: str, password: str) -> str:
    api = url.rstrip("/") + "/api/token-auth/"
    body = urllib.parse.urlencode({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        api,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Autenticacion fallida ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"No se pudo conectar a {url}. ¿WebODM en marcha? (Iniciar WebODM.bat)"
        ) from exc

    token = data.get("token")
    if not token:
        raise RuntimeError(f"Respuesta sin token: {data}")
    return token


def test_token(url: str, token: str) -> int:
    api = url.rstrip("/") + "/api/projects/"
    req = urllib.request.Request(api, headers={"Authorization": f"JWT {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            print("Token rechazado o expirado (403). Ejecuta con --force.")
            return 2
        raise
    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        count = data.get("count", len(data.get("results", [])))
    else:
        count = 0
    print(f"API OK — proyectos visibles: {count}")
    return 0


def save_token(token: str) -> None:
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(token.strip())
    print(f"Token guardado en: {TOKEN_PATH}")
    print("(Archivo ignorado por Git — no se commitea)")


def main() -> int:
    p = argparse.ArgumentParser(description="Obtener token JWT WebODM")
    p.add_argument("--username", type=str, help="Usuario WebODM")
    p.add_argument("--password", type=str, help="Contrasena (omitir para prompt)")
    p.add_argument("--url", type=str, help="URL WebODM (default: config)")
    p.add_argument("--force", action="store_true", help="Renovar aunque exista token")
    p.add_argument("--test", action="store_true", help="Probar token contra /api/projects/")
    args = p.parse_args()

    if os.path.isfile(TOKEN_PATH) and not args.force and not args.test:
        print(f"Ya existe {TOKEN_PATH}")
        print("Usa --force para renovar o --test para comprobar.")
        return 0

    if args.test and os.path.isfile(TOKEN_PATH) and not args.force:
        cfg = _load_config()
        url = args.url or cfg.get("url", "http://localhost:8000")
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return test_token(url, f.read().strip())

    cfg = _load_config()
    url = args.url or cfg.get("url", "http://localhost:8000")
    username = args.username or cfg.get("username") or ""
    password = args.password or cfg.get("password") or ""

    if not username:
        username = input("Usuario WebODM: ").strip()
    if not password:
        password = getpass.getpass("Contrasena WebODM: ")

    if not username or not password:
        print("Faltan credenciales. Usa webodm.local.json o --username/--password")
        return 1

    print(f"Conectando a {url} ...")
    token = fetch_token(url, username, password)
    save_token(token)

    if args.test:
        return test_token(url, token)
    print("Tip: python scripts/webodm_get_token.py --test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
