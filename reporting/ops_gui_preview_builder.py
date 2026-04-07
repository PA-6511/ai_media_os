from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
DEFAULT_SIDEBAR_JSON_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_CARDS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
DEFAULT_TABS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}


def _normalize_path(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        return "N/A"

    path_obj = Path(text)
    if path_obj.is_absolute():
        try:
            return str(path_obj.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(path_obj)

    return text.replace("\\", "/")


def _text_or_na(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else "N/A"


def _escape(value: Any) -> str:
    return html.escape(_text_or_na(value))


def _status_tone(value: Any) -> str:
    text = _text_or_na(value).upper()
    if text in {"RELEASE", "READY", "OK", "AVAILABLE"}:
        return "good"
    if text in {"REVIEW", "WARNING", "C", "B"}:
        return "warn"
    if text in {"HOLD", "ERROR", "FAIL", "CRITICAL", "D", "F"}:
        return "bad"
    return "neutral"


def _header_value(header: dict[str, Any], status_light: dict[str, Any], key: str) -> Any:
    return header.get(key) if header.get(key) is not None else status_light.get(key)


def _source_item(path: Path, payload: dict[str, Any]) -> str:
    state = "OK" if payload else "N/A"
    state_class = "ok" if payload else "na"
    return (
        "<div class='source-pill'>"
        f"<span class='source-name'>{html.escape(path.name)}</span>"
        f"<span class='source-state source-{state_class}'>{state}</span>"
        "</div>"
    )


def _render_sidebar(sidebar: dict[str, Any]) -> str:
    sections = sidebar.get("sections") if isinstance(sidebar.get("sections"), list) else []
    if not sections:
        return "<div class='empty'>N/A</div>"

    blocks: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue

        title = _escape(section.get("title") or section.get("key"))
        items = section.get("items") if isinstance(section.get("items"), list) else []
        item_rows: list[str] = []

        if not items:
            item_rows.append("<li class='nav-item empty-inline'>N/A</li>")
        else:
            for item in items:
                if not isinstance(item, dict):
                    continue
                label = _escape(item.get("label") or item.get("key"))
                path = _escape(_normalize_path(item.get("path")))
                item_rows.append(
                    "<li class='nav-item'>"
                    f"<span class='nav-label'>{label}</span>"
                    f"<span class='nav-path'>{path}</span>"
                    "</li>"
                )

        blocks.append(
            "<section class='sidebar-section'>"
            f"<h3>{title}</h3>"
            f"<ul class='nav-list'>{''.join(item_rows)}</ul>"
            "</section>"
        )

    return "".join(blocks) or "<div class='empty'>N/A</div>"


def _render_tabs(tabs: dict[str, Any]) -> str:
    tabs_list = tabs.get("tabs") if isinstance(tabs.get("tabs"), list) else []
    if not tabs_list:
        return "<div class='empty'>N/A</div>"

    chips: list[str] = []
    details: list[str] = []
    for tab in tabs_list:
        if not isinstance(tab, dict):
            continue
        title = _escape(tab.get("title") or tab.get("key"))
        primary_path = _escape(_normalize_path(tab.get("primary_path")))
        tab_class = "tab-chip active" if tab.get("default") else "tab-chip"
        chips.append(f"<div class='{tab_class}'>{title}</div>")
        details.append(
            "<div class='tab-detail'>"
            f"<div class='tab-title'>{title}</div>"
            f"<div class='tab-path'>{primary_path}</div>"
            "</div>"
        )

    return (
        f"<div class='tabs-row'>{''.join(chips)}</div>"
        f"<div class='tabs-details'>{''.join(details)}</div>"
    )


def _render_cards(cards_payload: dict[str, Any], limit: int = 6) -> str:
    cards = cards_payload.get("cards") if isinstance(cards_payload.get("cards"), list) else []
    if not cards:
        return "<div class='empty'>N/A</div>"

    blocks: list[str] = []
    for card in cards[:limit]:
        if not isinstance(card, dict):
            continue
        title = _escape(card.get("title"))
        subtitle = _escape(card.get("subtitle"))
        status = _escape(card.get("status"))
        path = _escape(_normalize_path(card.get("path")))
        tone = _status_tone(card.get("status"))
        blocks.append(
            "<article class='preview-card'>"
            f"<div class='card-status tone-{tone}'>{status}</div>"
            f"<h3>{title}</h3>"
            f"<p class='card-subtitle'>{subtitle}</p>"
            f"<div class='card-path'>{path}</div>"
            "</article>"
        )

    return f"<div class='cards-grid'>{''.join(blocks)}</div>" if blocks else "<div class='empty'>N/A</div>"


def build_ops_gui_preview_html() -> str:
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH)
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_JSON_PATH)
    cards = _safe_read_json(DEFAULT_CARDS_JSON_PATH)
    tabs = _safe_read_json(DEFAULT_TABS_JSON_PATH)
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH)

    generated_at = _now_iso()
    decision = _header_value(header, status_light, "decision")
    badge_text = _header_value(header, status_light, "badge_text")
    health_grade = _header_value(header, status_light, "health_grade")
    anomaly_overall = _header_value(header, status_light, "anomaly_overall")
    recommended_action = status_light.get("recommended_action")

    sources_html = "".join(
        [
            _source_item(DEFAULT_HEADER_JSON_PATH, header),
            _source_item(DEFAULT_SIDEBAR_JSON_PATH, sidebar),
            _source_item(DEFAULT_CARDS_JSON_PATH, cards),
            _source_item(DEFAULT_TABS_JSON_PATH, tabs),
            _source_item(DEFAULT_STATUS_LIGHT_JSON_PATH, status_light),
        ]
    )

    sidebar_html = _render_sidebar(sidebar)
    tabs_html = _render_tabs(tabs)
    cards_html = _render_cards(cards)

    return f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>AI Media OS GUI Preview</title>
<style>
  :root {{
    --bg: #eef3ed;
    --panel: rgba(255, 255, 255, 0.88);
    --panel-strong: #ffffff;
    --ink: #163127;
    --muted: #61756b;
    --line: rgba(22, 49, 39, 0.10);
    --accent: #1f7a5a;
    --accent-soft: #d8efe3;
    --warn: #b87418;
    --bad: #a63d40;
    --shadow: 0 18px 40px rgba(20, 44, 35, 0.10);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "IBM Plex Sans", "Hiragino Sans", "Noto Sans JP", sans-serif;
    color: var(--ink);
    background:
      radial-gradient(circle at top left, rgba(31, 122, 90, 0.14), transparent 34%),
      linear-gradient(180deg, #f6faf6 0%, var(--bg) 100%);
    min-height: 100vh;
  }}
  .page {{ max-width: 1380px; margin: 0 auto; padding: 24px; }}
  .hero {{
    background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(232,244,237,0.96));
    border: 1px solid var(--line);
    border-radius: 24px;
    box-shadow: var(--shadow);
    padding: 24px;
    margin-bottom: 20px;
  }}
  .eyebrow {{ color: var(--muted); font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; }}
  h1 {{ margin: 8px 0 10px; font-size: clamp(1.8rem, 3vw, 3rem); line-height: 1.05; }}
  .hero-copy {{ color: var(--muted); max-width: 72ch; margin: 0 0 18px; }}
  .hero-grid {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; align-items: start; }}
  .status-strip {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
  .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 14px 16px; }}
  .metric-label {{ color: var(--muted); font-size: 12px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.08em; }}
  .metric-value {{ font-size: 1rem; font-weight: 700; }}
  .status-card {{ background: #183a2f; color: #f4fbf7; border-radius: 20px; padding: 18px; min-height: 100%; }}
  .status-pill {{ display: inline-flex; padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.14); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
  .status-main {{ margin: 14px 0 8px; font-size: 1.6rem; font-weight: 700; }}
  .status-sub {{ color: rgba(244,251,247,0.78); font-size: 0.92rem; line-height: 1.5; }}
  .source-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
  .source-pill {{ display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.76); border: 1px solid var(--line); }}
  .source-name {{ font-size: 12px; color: var(--muted); }}
  .source-state {{ font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
  .source-ok {{ color: var(--accent); }}
  .source-na {{ color: var(--warn); }}
  .shell {{ display: grid; grid-template-columns: 290px 1fr; gap: 18px; }}
  .panel {{ background: var(--panel-strong); border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow); overflow: hidden; }}
  .panel-head {{ padding: 18px 20px 10px; }}
  .panel-title {{ margin: 0; font-size: 1rem; }}
  .panel-subtitle {{ margin: 6px 0 0; color: var(--muted); font-size: 0.9rem; }}
  .sidebar-body {{ padding: 0 14px 18px; }}
  .sidebar-section {{ padding: 8px 6px 12px; border-bottom: 1px solid var(--line); }}
  .sidebar-section:last-child {{ border-bottom: 0; }}
  .sidebar-section h3 {{ margin: 0 0 10px; font-size: 0.92rem; }}
  .nav-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }}
  .nav-item {{ background: #f7fbf8; border: 1px solid var(--line); border-radius: 14px; padding: 10px 12px; }}
  .nav-label {{ display: block; font-weight: 600; margin-bottom: 4px; }}
  .nav-path {{ display: block; font-size: 0.8rem; color: var(--muted); word-break: break-all; }}
  .main {{ display: grid; gap: 18px; }}
  .tabs-wrap {{ padding: 0 18px 18px; }}
  .tabs-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }}
  .tab-chip {{ padding: 11px 14px; border-radius: 999px; border: 1px solid var(--line); background: #f4f8f5; color: var(--ink); font-weight: 600; }}
  .tab-chip.active {{ background: var(--accent); color: #fff; border-color: transparent; }}
  .tabs-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
  .tab-detail {{ border: 1px solid var(--line); border-radius: 16px; padding: 12px; background: #fbfdfb; }}
  .tab-title {{ font-weight: 700; margin-bottom: 6px; }}
  .tab-path {{ font-size: 0.82rem; color: var(--muted); word-break: break-all; }}
  .cards-wrap {{ padding: 0 18px 18px; }}
  .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }}
  .preview-card {{ background: linear-gradient(180deg, #ffffff 0%, #f7fbf8 100%); border: 1px solid var(--line); border-radius: 18px; padding: 16px; min-height: 180px; }}
  .preview-card h3 {{ margin: 10px 0 8px; font-size: 1rem; }}
  .card-status {{ display: inline-flex; border-radius: 999px; padding: 6px 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
  .tone-good {{ background: #d9f3e7; color: #116142; }}
  .tone-warn {{ background: #fff0d8; color: #9b6110; }}
  .tone-bad {{ background: #fde0e2; color: #9e2f36; }}
  .tone-neutral {{ background: #e8ece9; color: #56665e; }}
  .card-subtitle {{ margin: 0 0 12px; color: var(--muted); min-height: 2.8em; }}
  .card-path {{ font-size: 0.82rem; color: var(--muted); word-break: break-all; }}
  .footer-meta {{ color: var(--muted); font-size: 0.86rem; padding: 16px 4px 0; }}
  .empty {{ padding: 18px; border: 1px dashed var(--line); border-radius: 16px; color: var(--muted); background: #f9fbf9; }}
  .empty-inline {{ color: var(--muted); }}
  @media (max-width: 980px) {{
    .hero-grid {{ grid-template-columns: 1fr; }}
    .shell {{ grid-template-columns: 1fr; }}
    .status-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  }}
  @media (max-width: 640px) {{
    .page {{ padding: 16px; }}
    .hero {{ padding: 18px; border-radius: 18px; }}
    .panel {{ border-radius: 18px; }}
    .status-strip {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
  <div class=\"page\">
    <header class=\"hero\">
      <div class=\"eyebrow\">AI Media OS GUI Preview</div>
      <h1>Static sample page for pre-implementation layout review</h1>
      <p class=\"hero-copy\">Existing JSON artifacts are projected into a lightweight HTML shell so the team can inspect header, sidebar, tabs, and top cards before a full GUI implementation.</p>
      <div class=\"hero-grid\">
        <div>
          <div class=\"status-strip\">
            <div class=\"metric\">
              <div class=\"metric-label\">Decision</div>
              <div class=\"metric-value\">{_escape(decision)}</div>
            </div>
            <div class=\"metric\">
              <div class=\"metric-label\">Badge</div>
              <div class=\"metric-value\">{_escape(badge_text)}</div>
            </div>
            <div class=\"metric\">
              <div class=\"metric-label\">Health Grade</div>
              <div class=\"metric-value\">{_escape(health_grade)}</div>
            </div>
            <div class=\"metric\">
              <div class=\"metric-label\">Anomaly</div>
              <div class=\"metric-value\">{_escape(anomaly_overall)}</div>
            </div>
          </div>
          <div class=\"source-row\">{sources_html}</div>
        </div>
        <aside class=\"status-card\">
          <div class=\"status-pill\">header status</div>
          <div class=\"status-main\">{_escape(decision)}</div>
          <div class=\"status-sub\">{_escape(recommended_action)}</div>
        </aside>
      </div>
    </header>

    <div class=\"shell\">
      <aside class=\"panel\">
        <div class=\"panel-head\">
          <h2 class=\"panel-title\">Sidebar</h2>
          <p class=\"panel-subtitle\">Sections and navigation items</p>
        </div>
        <div class=\"sidebar-body\">{sidebar_html}</div>
      </aside>

      <main class=\"main\">
        <section class=\"panel\">
          <div class=\"panel-head\">
            <h2 class=\"panel-title\">Tabs</h2>
            <p class=\"panel-subtitle\">Top-level views for GUI implementation</p>
          </div>
          <div class=\"tabs-wrap\">{tabs_html}</div>
        </section>

        <section class=\"panel\">
          <div class=\"panel-head\">
            <h2 class=\"panel-title\">Top Cards</h2>
            <p class=\"panel-subtitle\">Representative cards for above-the-fold layout</p>
          </div>
          <div class=\"cards-wrap\">{cards_html}</div>
        </section>
      </main>
    </div>

    <div class=\"footer-meta\">Generated at: {html.escape(generated_at)}</div>
  </div>
</body>
</html>
"""