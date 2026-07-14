# -*- coding: utf-8 -*-
"""
Restaura entregables PROT-VALLE-0B-REV03 y PROT-SAX-0F-OMEXOM tras pérdida de Proyectos/.

Fuentes fallback: Downloads, zip COM Valle, scripts extraídos del transcript.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
EXTRACT = REPO / "scripts" / "_restore_extract"

VALLE_DIR = REPO / "Proyectos" / "Colectora Valle" / "estudio protecciones julio"
SAX_DIR = REPO / "Proyectos" / "estudio coordinacion protecciones" / "nudo sax"

VALLE_PDF_OUT = VALLE_DIR / "VCO-SET-ME-O-0016.0B_Memoria_COM_REV03_12072026.pdf"

# COM mínimos Sax 0F (desde state + revisión previa) — suficiente para regenerar md/PDF
SAX_RCC_EXTRACT = """R12: C2=COM-1 | C3=Abierto | C4=20-24 | C5=Selectividad 67N Sax-Valle linea 132 kV | C6=OMEXOM: dial unificado en tablas | C7=REC Propiedad: incoherencia Tabla 16 vs 66; falta curva coordinacion
R13: C2=COM-2 | C3=Parcial | C4=15-20 | C5=Impedancias linea REE/Sax | C6=Actualizado tramo AT | C7=Verificar matriz LA1/LS1 comun con Valle
R14: C2=COM-3 | C3=Abierto | C4=55-57 | C5=Funcion 21 AT1 | C6=Ajustes documentados | C7=Falta evidencia selectividad MT/AT segun manual
R15: C2=COM-4 | C3=Abierto | C4=4-5, 8 | C5=Funcion 68 sin nota tecnica | C6=Indica aplicado | C7=Solicitar nota tecnica o esquema
R16: C2=COM-5 | C3=Abierto | C4=11-14 | C5=67N MT | C6=Pickup revisado | C7=Coordinacion con Valle pendiente
R17: C2=COM-6 | C3=Abierto | C4=30-35 | C5=87L linea | C6=600 A documentado | C7=Verificar teleproteccion tramo subterraneo
R18: C2=COM-7 | C3=Abierto | C4=62-70 | C5=FAT AT1 | C6=Parametros en tabla | C7=No cierra selectividad documentada
R19: C2=COM-8 | C3=Parcial | C4=45-47 | C5=27/59 | C6=Aplicado | C7=Confirmar rampas REE
R20: C2=COM-9 | C3=Parcial | C4=35-38 | C5=Impedancia duplex | C6=Valor actualizado | C7=Cruzar con IFC oficial
R21: C2=COM-10 | C3=Parcial | C4=22 | C5=51P/51TD | C6=Sin cambio | C7=Recalcular si aplica
R22: C2=COM-11 | C3=Abierto | C4=34, 81 | C5=Reenganche 79 | C6=Bloqueado segun OMEXOM | C7=Compilado muestra E79=Y — incoherente
"""


def _log(msg: str) -> None:
    print(msg, flush=True)


def _copy_first(pattern: str, dest: Path, downloads_only: bool = True) -> Path | None:
    roots = [DOWNLOADS] if downloads_only else [DOWNLOADS, REPO]
    for root in roots:
        if not root.is_dir():
            continue
        matches = sorted(root.glob(pattern))
        if matches:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(matches[0], dest)
            _log(f"  copiado: {matches[0].name} -> {dest}")
            return dest
    return None


def _extract_valle_pdf() -> Path | None:
    zips = sorted(DOWNLOADS.glob("VCO-SET-ME-O-0016.0B*COM*.zip"))
    if not zips:
        return None
    dest = VALLE_DIR / "VCO-SET-ME-O-0016.0B Memoria de Cálculo. Estudio de Coordinación de Protecciones (2).pdf"
    VALLE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zips[0]) as zf:
        pdf_names = [n for n in zf.namelist() if n.lower().endswith(".pdf") and "0016" in n]
        if not pdf_names:
            return None
        with zf.open(pdf_names[0]) as src, open(dest, "wb") as out:
            shutil.copyfileobj(src, out)
    _log(f"  extraido PDF Valle desde zip -> {dest.name}")
    return dest


def _deploy_scripts() -> None:
    mapping = {
        EXTRACT / "generar_respuesta_propiedad_rev03.py": VALLE_DIR / "generar_respuesta_propiedad_rev03.py",
        EXTRACT / "anotar_pdf_com_valle_julio.py": VALLE_DIR / "anotar_pdf_com_rev03.py",
    }
    sax_src = EXTRACT / "generar_revision_propiedad_sax_0F.py"
    if sax_src.is_file() and sax_src.read_text(encoding="utf-8").startswith("***"):
        _write_sax_generator(SAX_DIR / "generar_revision_propiedad_sax_0F.py")
    elif sax_src.is_file():
        mapping[sax_src] = SAX_DIR / "generar_revision_propiedad_sax_0F.py"

    for src, dst in mapping.items():
        if not src.is_file():
            raise FileNotFoundError(f"Falta script extraido: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_sax_generator(path: Path) -> None:
    raw = (EXTRACT / "generar_revision_propiedad_sax_0F.py").read_text(encoding="utf-8")
    lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("***"):
            continue
        if line.startswith("+") and not line.startswith("++"):
            lines.append(line[1:])
        elif line.startswith(" ") and lines:
            lines.append(line[1:] if line.startswith(" ") else line)
    # patch format uses + prefix; strip leading + from content lines
    body = "\n".join(
        ln[1:] if ln.startswith("+") else ln
        for ln in raw.splitlines()
        if not ln.startswith("***") and (ln.startswith("+") or (ln.startswith(" ") and ln.strip()))
    )
    # cleaner: only lines starting with +
    body = "\n".join(ln[1:] for ln in raw.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body + "\n", encoding="utf-8")
    _log(f"  generado: {path}")


def _patch_sax_loader(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "field_map" in text:
        return
    old = '''    rx = re.compile(
        r"R\\d+:\\s+C2=(COM-\\d+)\\s+\\|\\s+C3=([^|]+)\\|\\s+C4=([^|]+)\\|\\s+C5=([^|]+)\\|\\s+C6=([^|]+)\\|\\s+C7=([^|]+)",
        re.IGNORECASE,
    )

    items: list[ComItem] = []
    with open(RCC_TXT, "r", encoding="utf-8") as f:
        for line in f:
            m = rx.search(line)
            if not m:
                continue
            items.append(
                ComItem(
                    com=m.group(1).strip(),
                    status=m.group(2).strip(),
                    pages=m.group(3).strip(),
                    propiedad=m.group(4).strip(),
                    omexom=m.group(5).strip(),
                    propiedad_rev=m.group(6).strip(),
                )
            )
    return items'''
    new = '''    items: list[ComItem] = []
    with open(RCC_TXT, "r", encoding="utf-8") as f:
        for line in f:
            if "C2=COM-" not in line:
                continue
            line = re.sub(r"^R\\d+:\\s*", "", line.strip())
            fields: dict[str, str] = {}
            for part in line.split("|"):
                part = part.strip()
                m = re.match(r"^(C\\d+)=(.*)$", part)
                if m:
                    fields[m.group(1)] = m.group(2).strip()
            if "C2" not in fields:
                continue
            items.append(
                ComItem(
                    com=fields.get("C2", ""),
                    status=fields.get("C3", "Abierto"),
                    pages=fields.get("C4", ""),
                    propiedad=fields.get("C5", ""),
                    omexom=fields.get("C6", ""),
                    propiedad_rev=fields.get("C7", ""),
                )
            )
    return items'''
    if old in text:
        path.write_text(text.replace(old, new), encoding="utf-8")


def _run(cmd: list[str], cwd: Path) -> None:
    _log(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def restore_valle() -> None:
    _log("\n=== VALLE ===")
    VALLE_DIR.mkdir(parents=True, exist_ok=True)

    rcc = _copy_first("*RCC*.xlsx", VALLE_DIR / "VCO-SET-ME-O-0016.0A RCC source.xlsx")
    if not rcc:
        rcc = _copy_first("*Hoja Revision VALLE*.xlsx", VALLE_DIR / "VCO-SET-ME-O-0016.0B RCC source.xlsx")

    if not _extract_valle_pdf():
        _copy_first("VCO-SET-ME-O-0016.0B*.pdf", VALLE_DIR / "VCO-SET-ME-O-0016.0B Memoria de Cálculo. Estudio de Coordinación de Protecciones (2).pdf")

    _deploy_scripts()
    _run([sys.executable, "generar_respuesta_propiedad_rev03.py"], VALLE_DIR)

    # PDF anotado con nombre esperado en state.json
    annotate = VALLE_DIR / "anotar_pdf_com_rev03.py"
    code = f"""
import anotar_pdf_com_rev03 as m
src = m.find_pdf()
dst = r"{VALLE_PDF_OUT}"
_, out, n = m.annotate(src=src, dst=dst)
print("PDF:", out, "marcas:", n)
"""
    _run([sys.executable, "-c", code], VALLE_DIR)


def restore_sax() -> None:
    _log("\n=== SAX ===")
    SAX_DIR.mkdir(parents=True, exist_ok=True)

    pdf = _copy_first("SAX-SET-ME-O-0016-0F*.pdf", SAX_DIR / "SAX_MEMORIA_0F.pdf")
    if not pdf:
        raise FileNotFoundError("No encuentro SAX-SET-ME-O-0016-0F PDF en Downloads")

    (SAX_DIR / "_extract_sax_rcc.txt").write_text(SAX_RCC_EXTRACT.strip() + "\n", encoding="utf-8")
    _log("  escrito _extract_sax_rcc.txt (COM 1-11)")

    sax_script = SAX_DIR / "generar_revision_propiedad_sax_0F.py"
    if not sax_script.is_file():
        _write_sax_generator(sax_script)
    _patch_sax_loader(sax_script)

    _run([sys.executable, "generar_revision_propiedad_sax_0F.py"], SAX_DIR)


def main() -> int:
    _log("Restaurando entregables Valle + Sax...")
    restore_valle()
    restore_sax()
    _log("\nRestauracion completada. Ejecutar validador:")
    _log("  python scripts/validate_deliverables.py --state opengravity/runtime/tasks/PROT-VALLE-0B-REV03/state.json")
    _log("  python scripts/validate_deliverables.py --state opengravity/runtime/tasks/PROT-SAX-0F-OMEXOM/state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
