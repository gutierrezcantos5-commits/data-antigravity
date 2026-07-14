# -*- coding: utf-8 -*-
"""
Validacion cruzada ingenieria ↔ ortofoto (Antigravity Fase 4).

Compara el bbox WGS84 del emplazamiento (geo manifest / state.json)
con el bbox de la ortofoto (KMZ/KML/GeoTIFF exportado de WebODM).

Uso:
  python scripts/cross_validate.py --state opengravity/runtime/tasks/<id>/state.json
  python scripts/cross_validate.py --geo opengravity/runtime/geo/colectora_valle.geo.json --ortho-kmz path.kmz
  python scripts/cross_validate.py --site-bbox 38.57,-0.95,38.56,-0.94 --ortho-kmz path.kmz
    (orden: north,east,south,west)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_VERSION = "1"

# Umbral: % del area del sitio que debe solapar con la ortofoto
OVERLAP_OK = 0.80
OVERLAP_WARN = 0.20


@dataclass
class BBox:
    north: float
    south: float
    east: float
    west: float

    def valid(self) -> bool:
        return self.north > self.south and self.east > self.west

    def area(self) -> float:
        if not self.valid():
            return 0.0
        return (self.north - self.south) * (self.east - self.west)

    def to_dict(self) -> dict[str, float]:
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _bbox_from_dict(d: dict[str, Any]) -> BBox:
    return BBox(
        north=float(d["north"]),
        south=float(d["south"]),
        east=float(d["east"]),
        west=float(d["west"]),
    )


def _read_kml_text(path: str) -> str:
    if path.lower().endswith(".kmz"):
        with zipfile.ZipFile(path, "r") as kmz:
            for name in kmz.namelist():
                if name.lower().endswith(".kml"):
                    return kmz.read(name).decode("utf-8", errors="replace")
        raise ValueError(f"KMZ sin KML interno: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def bbox_from_kml_file(path: str) -> BBox:
    doc = _read_kml_text(path)

    def _tag(name: str) -> float:
        m = re.search(rf"<{name}>([-0-9.eE+]+)</{name}>", doc)
        if not m:
            raise ValueError(f"Etiqueta <{name}> no encontrada en {path}")
        return float(m.group(1))

    # LatLonBox en KMZ overlay o Region
    try:
        return BBox(
            north=_tag("north"),
            south=_tag("south"),
            east=_tag("east"),
            west=_tag("west"),
        )
    except ValueError:
        pass

    # coordinates: lon,lat,alt ...
    coords = re.findall(r"<coordinates>\s*([^<]+)\s*</coordinates>", doc)
    if not coords:
        raise ValueError(f"No se pudo extraer bbox de {path}")
    lons: list[float] = []
    lats: list[float] = []
    for block in coords:
        for pair in block.strip().split():
            parts = pair.split(",")
            if len(parts) >= 2:
                lons.append(float(parts[0]))
                lats.append(float(parts[1]))
    if not lons:
        raise ValueError(f"Coordenadas vacias en {path}")
    return BBox(north=max(lats), south=min(lats), east=max(lons), west=min(lons))


def bbox_from_geotiff(path: str) -> BBox:
    try:
        import rasterio
        from rasterio.warp import transform_bounds
    except ImportError as exc:
        raise RuntimeError(
            "GeoTIFF requiere rasterio: pip install rasterio"
        ) from exc

    with rasterio.open(path) as ds:
        b = ds.bounds
        if ds.crs and str(ds.crs) != "EPSG:4326":
            w, s, e, n = transform_bounds(ds.crs, "EPSG:4326", b.left, b.bottom, b.right, b.top)
            return BBox(north=n, south=s, east=e, west=w)
        return BBox(north=b.top, south=b.bottom, east=b.right, west=b.left)


def bbox_from_source(path: str) -> BBox:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".kmz", ".kml"):
        return bbox_from_kml_file(path)
    if ext in (".tif", ".tiff"):
        return bbox_from_geotiff(path)
    if ext == ".json":
        data = _load_json(path)
        if "site_bbox_wgs84" in data:
            return _bbox_from_dict(data["site_bbox_wgs84"])
        if "bbox_wgs84" in data:
            return _bbox_from_dict(data["bbox_wgs84"])
    raise ValueError(f"Formato no soportado para bbox: {path}")


def resolve_repo_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(REPO_ROOT, path))


def overlap_metrics(site: BBox, ortho: BBox) -> dict[str, Any]:
    lat_ov = min(site.north, ortho.north) - max(site.south, ortho.south)
    lon_ov = min(site.east, ortho.east) - max(site.west, ortho.west)

    if lat_ov <= 0 or lon_ov <= 0:
        return {
            "overlap_area": 0.0,
            "site_area": site.area(),
            "ortho_area": ortho.area(),
            "overlap_ratio_site": 0.0,
            "overlap_ratio_ortho": 0.0,
            "site_inside_ortho": False,
            "intersects": False,
        }

    ov_area = lat_ov * lon_ov
    site_area = site.area()
    ortho_area = ortho.area()
    inside = (
        site.south >= ortho.south
        and site.north <= ortho.north
        and site.west >= ortho.west
        and site.east <= ortho.east
    )
    return {
        "overlap_area": ov_area,
        "site_area": site_area,
        "ortho_area": ortho_area,
        "overlap_ratio_site": ov_area / site_area if site_area else 0.0,
        "overlap_ratio_ortho": ov_area / ortho_area if ortho_area else 0.0,
        "site_inside_ortho": inside,
        "intersects": True,
    }


def classify_severity(metrics: dict[str, Any]) -> tuple[str, bool, list[dict[str, str]]]:
    alerts: list[dict[str, str]] = []
    ratio = metrics.get("overlap_ratio_site") or 0.0
    inside = metrics.get("site_inside_ortho", False)
    intersects = metrics.get("intersects", False)

    if not intersects:
        alerts.append(
            {
                "code": "GEO_NO_OVERLAP",
                "severity": "red",
                "message": "El emplazamiento no solapa con la ortofoto.",
            }
        )
        return "red", False, alerts

    if inside:
        alerts.append(
            {
                "code": "GEO_SITE_INSIDE_ORTHO",
                "severity": "green",
                "message": "Emplazamiento completamente dentro de la ortofoto.",
            }
        )
        return "green", True, alerts

    if ratio >= OVERLAP_OK:
        alerts.append(
            {
                "code": "GEO_PARTIAL_OVERLAP_OK",
                "severity": "green",
                "message": f"Solapamiento aceptable ({ratio * 100:.1f}% del sitio).",
            }
        )
        return "green", True, alerts

    if ratio >= OVERLAP_WARN:
        alerts.append(
            {
                "code": "GEO_PARTIAL_OVERLAP_WARN",
                "severity": "yellow",
                "message": f"Solapamiento parcial ({ratio * 100:.1f}% del sitio). Revisar cobertura.",
            }
        )
        return "yellow", False, alerts

    alerts.append(
        {
            "code": "GEO_SITE_OUTSIDE_ORTHO",
            "severity": "red",
            "message": f"Cobertura insuficiente ({ratio * 100:.1f}% del sitio).",
        }
    )
    return "red", False, alerts


def load_site_from_geo_manifest(path: str) -> tuple[BBox, dict[str, Any]]:
    data = _load_json(path)
    bbox = _bbox_from_dict(data["site_bbox_wgs84"])
    return bbox, data


def load_from_state(state_path: str) -> tuple[BBox, str | None, str, dict[str, Any]]:
    state = _load_json(state_path)
    geo = state.get("geo_link") or {}
    manifest = geo.get("manifest") or geo.get("geo_manifest")
    ortho = geo.get("orthophoto_file") or geo.get("ortho_file")

    if manifest:
        manifest_path = resolve_repo_path(manifest)
        site, geo_data = load_site_from_geo_manifest(manifest_path)
        if not ortho:
            ortho = geo_data.get("orthophoto_file")
        return site, ortho, state.get("task_id") or os.path.basename(os.path.dirname(state_path)), state

    if geo.get("site_bbox_wgs84"):
        site = _bbox_from_dict(geo["site_bbox_wgs84"])
        return site, ortho, state.get("task_id") or "unknown", state

    raise ValueError(
        "state.json sin geo_link.manifest ni geo_link.site_bbox_wgs84"
    )


def run_cross_validation(
    site: BBox,
    ortho_path: str,
    task_id: str = "AD-HOC",
    site_label: str = "site",
    ortho_label: str = "orthophoto",
) -> dict[str, Any]:
    if not site.valid():
        raise ValueError("BBox del emplazamiento invalido")

    ortho = bbox_from_source(ortho_path)
    if not ortho.valid():
        raise ValueError(f"BBox ortofoto invalido: {ortho_path}")

    metrics = overlap_metrics(site, ortho)
    severity, passed, alerts = classify_severity(metrics)

    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "validated_at": _utc_now(),
        "passed": passed,
        "severity": severity,
        "site": {"label": site_label, "bbox_wgs84": site.to_dict()},
        "orthophoto": {
            "label": ortho_label,
            "file": ortho_path,
            "bbox_wgs84": ortho.to_dict(),
        },
        "metrics": metrics,
        "alerts": alerts,
    }


def write_task_result(state_path: str, result: dict[str, Any]) -> str:
    task_dir = os.path.dirname(os.path.abspath(state_path))
    out_path = os.path.join(task_dir, "cross_validation.json")
    _save_json(out_path, result)

    state = _load_json(state_path)
    validation = state.setdefault("validation", {})
    validation["cross_geo"] = {
        "last_run": result["validated_at"],
        "last_result": "passed" if result["passed"] else "failed",
        "severity": result["severity"],
        "file": "cross_validation.json",
    }
    geo_link = state.setdefault("geo_link", {})
    geo_link["last_cross_validation"] = result["validated_at"]
    state["updated_at"] = result["validated_at"][:10]
    _save_json(state_path, state)
    return out_path


def _print_result(result: dict[str, Any]) -> int:
    print("=== VALIDACION CRUZADA GEO ===")
    print(f"task_id: {result['task_id']}")
    print(f"severity: {result['severity']} | passed: {result['passed']}")
    m = result["metrics"]
    print(
        f"overlap_ratio_site: {m.get('overlap_ratio_site', 0) * 100:.1f}% | "
        f"inside: {m.get('site_inside_ortho')}"
    )
    for a in result.get("alerts") or []:
        print(f"  [{a.get('severity')}] {a.get('code')}: {a.get('message')}")
    return 0 if result["passed"] else 2


def main() -> int:
    p = argparse.ArgumentParser(description="Cross-validacion ingenieria vs ortofoto")
    p.add_argument("--state", type=str, help="Ruta a state.json con geo_link")
    p.add_argument("--geo", type=str, help="Manifiesto geo JSON (site bbox)")
    p.add_argument("--ortho-kmz", type=str, help="KMZ/KML/GeoTIFF ortofoto")
    p.add_argument("--ortho", type=str, help="Alias de --ortho-kmz")
    p.add_argument(
        "--site-bbox",
        type=str,
        help="BBox sitio manual: north,east,south,west (WGS84)",
    )
    args = p.parse_args()

    ortho_path = args.ortho_kmz or args.ortho
    state_path = args.state

    try:
        if state_path:
            site, ortho_from_state, task_id, _state = load_from_state(state_path)
            ortho_path = ortho_path or ortho_from_state
            if not ortho_path:
                raise ValueError("Falta orthophoto_file en geo_link o --ortho-kmz")
            ortho_path = resolve_repo_path(ortho_path) if not os.path.isabs(ortho_path) else ortho_path
            result = run_cross_validation(site, ortho_path, task_id=task_id)
            out = write_task_result(state_path, result)
            code = _print_result(result)
            print(f"\nEscrito: {out}")
            return code

        if args.geo:
            site, geo_data = load_site_from_geo_manifest(resolve_repo_path(args.geo))
            ortho_path = ortho_path or geo_data.get("orthophoto_file")
            if not ortho_path:
                raise ValueError("Falta --ortho-kmz o orthophoto_file en geo manifest")
            if not os.path.isabs(ortho_path):
                ortho_path = resolve_repo_path(ortho_path)
            result = run_cross_validation(
                site,
                ortho_path,
                task_id=geo_data.get("project_id") or "AD-HOC",
                site_label=geo_data.get("name") or "site",
            )
            return _print_result(result)

        if args.site_bbox and ortho_path:
            parts = [float(x.strip()) for x in args.site_bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("--site-bbox requiere north,east,south,west")
            site = BBox(north=parts[0], east=parts[1], south=parts[2], west=parts[3])
            if not os.path.isabs(ortho_path):
                ortho_path = resolve_repo_path(ortho_path)
            result = run_cross_validation(site, ortho_path)
            return _print_result(result)

        p.print_help()
        return 1

    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERR | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
