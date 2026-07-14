# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

TASKS_ROOT = os.path.join(REPO_ROOT, "opengravity", "runtime", "tasks")
EVALS_JSON = os.path.join(REPO_ROOT, "opengravity", "runtime", "evals", "engineering_cases.json")
MEMORY_INDEX = os.path.join(REPO_ROOT, "opengravity", "runtime", "memory", "index.json")
GEO_DIR = os.path.join(REPO_ROOT, "opengravity", "runtime", "geo")

SAX_FOLDER = os.path.join(
    REPO_ROOT,
    "Proyectos",
    "estudio coordinacion protecciones",
    "nudo sax",
)
VALLE_FOLDER = os.path.join(
    REPO_ROOT,
    "Proyectos",
    "Colectora Valle",
    "estudio protecciones julio",
)


def _load_evals() -> dict:
    with open(EVALS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def repo_root() -> str:
    return REPO_ROOT


@pytest.fixture(scope="session")
def eval_cases() -> dict:
    return _load_evals()


@pytest.fixture(scope="session")
def local_deliverables_available() -> bool:
    sax_state = os.path.join(TASKS_ROOT, "PROT-SAX-0F-OMEXOM", "state.json")
    if not os.path.isfile(sax_state):
        return False
    with open(sax_state, "r", encoding="utf-8") as f:
        state = json.load(f)
    for path in state.get("deliverables", {}).get("produced") or []:
        if not os.path.isfile(path):
            return False
    valle_state = os.path.join(TASKS_ROOT, "PROT-VALLE-0B-REV03", "state.json")
    if not os.path.isfile(valle_state):
        return False
    with open(valle_state, "r", encoding="utf-8") as f:
        state = json.load(f)
    for path in state.get("deliverables", {}).get("produced") or []:
        if not os.path.isfile(path):
            return False
    return True


@pytest.fixture(scope="session")
def skip_local(local_deliverables_available: bool):
    if not local_deliverables_available:
        pytest.skip("Entregables locales no disponibles (Proyectos/ fuera de disco)")
