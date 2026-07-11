"""Map scene renderer — the signature shot of premium geography channels.

Downloads world coastline GeoJSON once (cached in ~/.cache/terra_maps, runs
on the GitHub runner), then renders two dark branded map PNGs with PIL:
  world.png  — full equirectangular world, for the zoom-out phase
  region.png — re-rendered close-up around the target, for the zoom-in phase
The Remotion MapZoom component animates world -> region with a pulsing
marker and a Hindi label chip.

FAIL-OPEN: any problem returns None and the scene falls back to b-roll.
"""
import json
import os

import requests
from PIL import Image, ImageDraw

GEOJSON_URL = ("https://raw.githubusercontent.com/johan/world.geo.json/"
               "master/countries.geo.json")
NAVY = (10, 20, 40)
LAND = (22, 41, 74)
LAND_EDGE = (58, 92, 150)
GRID = (26, 42, 72)


def _cache_dir() -> str:
    d = os.path.join(os.path.expanduser("~"), ".cache", "terra_maps")
    os.makedirs(d, exist_ok=True)
    return d


def _load_world() -> list | None:
    path = os.path.join(_cache_dir(), "world.geo.json")
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 100_000:
            print("[map] downloading world coastlines ...")
            r = requests.get(GEOJSON_URL, timeout=120)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        with open(path, encoding="utf-8") as f:
            gj = json.load(f)
        polys = []
        for feat in gj.get("features", []):
            geom = feat.get("geometry") or {}
            if geom.get("type") == "Polygon":
                polys.extend(geom["coordinates"])
            elif geom.get("type") == "MultiPolygon":
                for mp in geom["coordinates"]:
                    polys.extend(mp)
        return polys  # list of rings [[lon, lat], ...]
    except Exception as e:
        print(f"[map] coastline data unavailable ({e}) — map scenes fall back")
        return None


def _render(polys: list, bbox: tuple, size: tuple, grid_step: float) -> Image.Image:
    """bbox = (lon_min, lat_min, lon_max, lat_max), equirectangular."""
    w, h = size
    lon0, lat0, lon1, lat1 = bbox

    def xy(lon: float, lat: float) -> tuple:
        return ((lon - lon0) / (lon1 - lon0) * w,
                (lat1 - lat) / (lat1 - lat0) * h)

    img = Image.new("RGB", (w, h), NAVY)
    d = ImageDraw.Draw(img)
    # graticule
    lon = -180.0
    while lon <= 180:
        x, _ = xy(lon, 0)
        if 0 <= x <= w:
            d.line([(x, 0), (x, h)], fill=GRID, width=1)
        lon += grid_step
    lat = -90.0
    while lat <= 90:
        _, y = xy(0, lat)
        if 0 <= y <= h:
            d.line([(0, y), (w, y)], fill=GRID, width=1)
        lat += grid_step
    # land
    for ring in polys:
        if len(ring) < 3:
            continue
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        if max(lons) < lon0 or min(lons) > lon1 or max(lats) < lat0 or min(lats) > lat1:
            continue  # completely outside view
        pts = [xy(p[0], p[1]) for p in ring]
        d.polygon(pts, fill=LAND, outline=LAND_EDGE)
    return img


def render_scene_maps(lat: float, lon: float, workdir: str, scene_n: int,
                      portrait: bool) -> dict | None:
    """Returns {world, region, markerWorld: [fx,fy], markerRegion: [fx,fy]}
    (paths are basenames inside workdir) or None."""
    try:
        polys = _load_world()
        if not polys:
            return None
        lat = max(min(float(lat), 85.0), -85.0)
        lon = max(min(float(lon), 179.9), -179.9)
        size = (2160, 3840) if portrait else (3840, 2160)
        aspect = size[0] / size[1]

        # world view: full longitudes, latitude span to fit aspect, centered
        # to keep the marker visible
        lat_span_w = 360 / aspect
        lat_c = max(min(0.0 if abs(lat) < lat_span_w / 2 - 5 else lat, 90 - lat_span_w / 2), lat_span_w / 2 - 90) if lat_span_w < 180 else 0.0
        if lat_span_w >= 180:
            bbox_w = (-180, -90, 180, 90)
        else:
            bbox_w = (-180, lat_c - lat_span_w / 2, 180, lat_c + lat_span_w / 2)
        world = _render(polys, bbox_w, size, grid_step=30)

        # region view: ~36 deg lon window around target (or narrower portrait)
        lon_span = 24.0 if portrait else 40.0
        lat_span = lon_span / aspect
        r_lat = max(min(lat, 90 - lat_span / 2), lat_span / 2 - 90)
        bbox_r = (lon - lon_span / 2, r_lat - lat_span / 2,
                  lon + lon_span / 2, r_lat + lat_span / 2)
        region = _render(polys, bbox_r, size, grid_step=5)

        def frac(bbox: tuple) -> list:
            fx = (lon - bbox[0]) / (bbox[2] - bbox[0])
            fy = (bbox[3] - lat) / (bbox[3] - bbox[1])
            return [round(min(max(fx, 0.02), 0.98), 4),
                    round(min(max(fy, 0.02), 0.98), 4)]

        wname = f"map_s{scene_n:02d}_world.png"
        rname = f"map_s{scene_n:02d}_region.png"
        world.save(os.path.join(workdir, wname))
        region.save(os.path.join(workdir, rname))
        print(f"[map] scene {scene_n}: rendered world+region maps "
              f"({lat:.2f}, {lon:.2f})")
        return {"world": wname, "region": rname,
                "markerWorld": frac(bbox_w), "markerRegion": frac(bbox_r)}
    except Exception as e:
        print(f"[map] render failed ({e}) — scene falls back to b-roll")
        return None
