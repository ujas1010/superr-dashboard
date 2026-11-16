"""Phase 13 - Offline dashboard: one self-contained HTML file (data + d3 embedded, no internet needed).

Output: submission/SupeRR_Pressure_Dashboard.html  (double-click to open in any browser)
        docs/index.html                              (same file, served by GitHub Pages)
Uses the same page as the online dashboard (pipeline/templates/dashboard_page.html) with a small local stand-in
for the online dashboard runtime (`dash.data`, `dash.draw`, ...).
"""
import json

import config as C

HERE = C.ROOT / "pipeline"
OUT = C.SUBMISSION / "SupeRR_Pressure_Dashboard.html"
PAGES = C.DOCS / "index.html"

TOKENS = """
:root {
  --color-fg:#14181f; --color-fg-muted:#5a6270; --color-bg:#ffffff; --color-panel:#f6f7f9; --color-border-line:#e1e4ea;
  --color-ok:#16865a; --color-warn:#b7791f; --color-bad:#c53030;
  --font-anthropic-sans: "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
  --font-anthropic-serif: Cambria, Georgia, "Times New Roman", serif;
  --cds-font-size-caption:12px; --cds-font-size-body:14px; --cds-font-size-heading:18px; --cds-font-size-title:30px;
  --cds-font-weight-medium:600;
  --cds-gap-xs:4px; --cds-gap-sm:8px; --cds-gap-md:12px; --cds-gap-lg:18px; --cds-gap-xl:28px;
  --cds-pad-xs:4px; --cds-pad-sm:8px; --cds-pad-md:12px; --cds-pad-lg:18px; --cds-pad-xl:28px; --cds-radius:8px;
  --cds-chart-muted:#b9bdc6; --cds-chart-grid:#eceef2; --cds-chart-axis:#c4c8d0; --cds-chart-reference:#8a909c;
  --cds-text-secondary:#5a6270; --cds-surface-popover:#ffffff; --cds-border:#d7dbe2; --cds-shadow-popover:0 4px 14px rgba(20,24,31,.14);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-fg:#e8eaee; --color-fg-muted:#a3aab6; --color-bg:#14171c; --color-panel:#1c2027; --color-border-line:#2d333d;
    --color-ok:#3fbf86; --color-warn:#e0a743; --color-bad:#ef6b6b;
    --cds-chart-muted:#596170; --cds-chart-grid:#262b33; --cds-chart-axis:#3a414c; --cds-chart-reference:#8a93a1;
    --cds-text-secondary:#a3aab6; --cds-surface-popover:#232832; --cds-border:#363d48; --cds-shadow-popover:0 4px 14px rgba(0,0,0,.5);
    color-scheme: dark;
  }
}
[hidden] { display:none !important; }
html, body { margin:0; background:var(--color-bg); color:var(--color-fg); }
#dash-root { max-width:1200px; margin:0 auto; padding:28px max(16px, 3vw) 48px; font-family:var(--font-anthropic-sans); font-size:14px; }
.dash-select { font:inherit; font-size:13px; padding:6px 10px; border-radius:6px; border:1px solid var(--color-border-line); background-color:var(--color-bg); color:var(--color-fg); }
"""

SHIM = """
window.dash = (function () {
  const DATA = JSON.parse(document.getElementById('dash-data').textContent);
  const draws = {};
  const api = {
    colors: ['#2a78d6', '#eb6834', '#1baf7a', '#e87ba4'],
    loader() {},                                  // data is embedded; tables are read directly
    data(id) {
      const t = DATA.tables[id];
      return t ? { status: 'ok', data: t, columns: Object.keys(t[0] || {}), meta: DATA.meta }
               : { status: 'missing', data: [], columns: [] };
    },
    draw(name, fn) { if (fn) { draws[name] = fn; } else { run(name); } },
    onData(fn) { fn(); },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    params() { return {}; }, setParams() {}, resetParams() {},
  };
  function run(name) {
    document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => {
      if (el.closest('[hidden]')) return;
      try { draws[name](el); } catch (e) { console.error(name, e); }
    });
  }
  api._runAll = () => Object.keys(draws).forEach(run);
  return api;
})();
"""

BOOT = """
(function () {
  // ?tab=pressure opens that tab (same as clicking it)
  const q = new URLSearchParams(location.search).get('tab');
  if (q) document.querySelectorAll('.pp-tab[data-tab="' + q + '"]').forEach((b) => b.click());
  window.scrollTo(0, 0);
  dash._runAll();
  // redraw when a tab is shown (drawings inside hidden sections are skipped) and on resize
  new MutationObserver(() => dash._runAll()).observe(document.getElementById('dash-root'),
    { attributes: true, attributeFilter: ['hidden'], subtree: true });
  let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => dash._runAll(), 150); });
})();
"""


def main():
    page = (HERE / "templates" / "dashboard_page.html").read_text(encoding="utf-8")
    data = (C.OUT / "dashboard" / "superr_dashboard_data.json").read_text(encoding="utf-8")
    d3js = (C.ROOT / "deck" / "node_modules" / "d3" / "dist" / "d3.min.js").read_text(encoding="utf-8")
    safe = data.replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SupeRR Pressure Dashboard</title>
<style>{TOKENS}</style>
<script>{d3js}</script>
<script id="dash-data" type="application/json">{safe}</script>
<script>{SHIM}</script>
</head><body>
<div id="dash-root">
{page}
</div>
<script>{BOOT}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    PAGES.write_text(html, encoding="utf-8")
    (C.DOCS / ".nojekyll").write_text("")
    print("offline dashboard:", OUT, round(OUT.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
