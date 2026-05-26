from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
TRANSIT_JS = REPO_ROOT / "frontend" / "js" / "transit.js"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_transit_panel_core_ids_exist() -> None:
    html = _read_text(INDEX_HTML)
    required_ids = [
        'id="btnCompareRoutes"',
        'id="multimodalPanel"',
        'id="multimodalResults"',
        'id="rightChatPanel"',
        'id="rightChatCollapse"',
        'id="rightChatExpand"',
    ]
    for required in required_ids:
        assert required in html, f"Missing core UI id in index.html: {required}"


def test_transit_route_api_exports_exist() -> None:
    js = _read_text(TRANSIT_JS)
    assert "function clearTransitRoute()" in js
    assert "window.clearTransitRoute = clearTransitRoute;" in js
    assert "window.showTransitRoute = function (optionIndex)" in js


def test_transit_segment_rendering_rules_present() -> None:
    js = _read_text(TRANSIT_JS)
    assert 'seg.mode === "bus" || seg.mode === "rail" || seg.mode === "ferry"' in js
    assert 'dashArray: isFerry ? "10,8" : null' in js
    assert 'dashArray: "2,8"' in js


def test_transit_graceful_draw_and_fitbounds_guards_present() -> None:
    js = _read_text(TRANSIT_JS)
    assert "if (!Array.isArray(displayCoords) || displayCoords.length < 2) return false;" in js
    assert "map.fitBounds(allBounds, { padding: [40, 40], maxZoom: 16 });" in js
    assert "const isEndpointWalk = idx === 0 || idx === (option.segments.length - 1);" in js
