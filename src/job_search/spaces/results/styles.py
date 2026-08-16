"""Theme + stylesheet for the results viewer.

Deliberately NOT the search Space's `common/theme.py`: that file is 1,000+ lines of aurora
blobs, glass panels and Gradio-override nukes tuned for a demo. A reader wants a quiet,
dense, readable page. Colours come from Gradio's theme variables so light/dark just works.
"""
from __future__ import annotations

import gradio as gr

theme = gr.themes.Base(
    primary_hue="indigo",
    neutral_hue="slate",
    radius_size=gr.themes.sizes.radius_md,
    spacing_size=gr.themes.sizes.spacing_sm,
    text_size=gr.themes.sizes.text_md,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "-apple-system", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill="#f6f7fb",
    body_background_fill_dark="#0f1117",
    block_background_fill="white",
    block_background_fill_dark="#161a23",
    block_border_color="#e5e7ef",
    block_border_color_dark="#262b38",
    input_background_fill="white",
    input_background_fill_dark="#11141c",
    button_primary_background_fill="var(--primary-600)",
    button_primary_background_fill_hover="var(--primary-700)",
    button_primary_text_color="white",
)

CSS = """
:root {
  --rv-max: 960px;
  --rv-high: #16a34a;
  --rv-mid: #d97706;
  --rv-low: #6b7280;
  --rv-bg: #f4f5f9;
  --rv-surface: #ffffff;
  --rv-surface-2: #f1f3f8;
  --rv-border: #e2e5ee;
  --rv-text: #111827;
  --rv-muted: #5b6474;
  --rv-link: #4f46e5;
}
.dark, .dark .gradio-container {
  --rv-bg: #0f1117;
  --rv-surface: #171b25;
  --rv-surface-2: #1f2430;
  --rv-border: #2b3140;
  --rv-text: #e6e8ee;
  --rv-muted: #9aa3b5;
  --rv-link: #a5b4fc;
}
body, .gradio-container { background: var(--rv-bg) !important; color: var(--rv-text); }
.gradio-container { max-width: var(--rv-max) !important; margin: 0 auto !important; }
.gradio-container footer { display: none !important; }  /* Gradio’s own footer; cards use no <footer> */

/* ---- header ---- */
#rv-header { padding: 28px 0 8px; }
#rv-header h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; margin: 0; }
#rv-header p { margin: 4px 0 0; color: var(--rv-muted); }
.rv-profile-chip {
  color: var(--rv-text); display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 0.85rem;
  padding: 4px 10px; border-radius: 999px;
  background: var(--rv-surface); border: 1px solid var(--rv-border);
}

/* ---- gate ---- */
#rv-gate { max-width: 460px; margin: 48px auto; }
#rv-gate .rv-gate-card { padding: 16px; border-radius: 14px; }
#rv-gate-error, #rv-gate-error * { color: #dc2626 !important; font-size: 0.9rem; }
#rv-gate-error { min-height: 1.4em; margin-top: 8px; }

/* ---- stats ---- */
.rv-stats { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 4px; }
.rv-stat {
  flex: 1 1 120px; background: var(--rv-surface); border: 1px solid var(--rv-border);
  border-radius: 10px; padding: 10px 14px; display: flex; flex-direction: column;
}
.rv-stat-n { color: var(--rv-text); font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.rv-stat-l { font-size: 0.75rem; color: var(--rv-muted); text-transform: uppercase; letter-spacing: 0.04em; }

/* ---- toolbar ---- */
#rv-toolbar {
  background: var(--rv-surface); border: 1px solid var(--rv-border);
  border-radius: 12px; padding: 8px 12px; margin: 10px 0 14px;
  align-items: end; gap: 24px;
}
#rv-toolbar .block, #rv-toolbar .form { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0; }
#rv-toolbar label > span, #rv-toolbar label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--rv-muted); }

/* ---- tabs ---- */
.tabs > .tab-nav, .tab-nav { border-bottom: 1px solid var(--rv-border) !important; margin-bottom: 8px; }
.tab-nav button { font-weight: 600 !important; color: var(--rv-muted) !important; }
.tab-nav button.selected { color: var(--rv-text) !important; border-color: var(--rv-link) !important; }
.tabitem { padding: 8px 0 !important; border: none !important; }

/* ---- instructions page ---- */
.rv-instr-card { background: var(--rv-surface) !important; border: 1px solid var(--rv-border) !important; border-radius: 12px !important; padding: 16px 18px !important; margin: 14px 0 !important; }
.rv-instr-card h3 { margin: 0 0 2px; font-size: 1rem; }
.rv-instr-card > .prose p, .rv-instr-card .prose p { color: var(--rv-muted); margin: 0 0 8px; font-size: 0.9rem; }
.rv-instr-card .form, .rv-instr-card .block, .rv-instr-card > div { background: transparent !important; border: none !important; box-shadow: none !important; }
.rv-instr-card #rv-prefs > div { border-left: none !important; }
.rv-instr textarea { font-family: var(--font-mono); font-size: 0.85rem; line-height: 1.5; }
#rv-prefs { gap: 10px; }
#rv-task-msg, #rv-task-msg * { color: var(--rv-muted); font-size: 0.9rem; }

/* ---- pager ---- */
.rv-pager { align-items: center; gap: 8px; margin: 12px 0 32px; }
.rv-pager-label { color: var(--rv-muted); font-size: 0.85rem; text-align: center; font-variant-numeric: tabular-nums; }

/* ---- list + cards ---- */
.rv-list { display: flex; flex-direction: column; gap: 10px; }
.rv-card {
  display: grid; grid-template-columns: 72px 1fr; gap: 0;
  background: var(--rv-surface); border: 1px solid var(--rv-border);
  border-radius: 12px; overflow: hidden;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.rv-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.06); }
.rv-card.is-applied  { border-color: var(--rv-high); }
.rv-score {
  display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding-top: 18px;
  color: white; font-variant-numeric: tabular-nums; line-height: 1;
}
.rv-score b { font-size: 1.5rem; font-weight: 700; }
.rv-score small { font-size: 0.7rem; opacity: .85; margin-top: 2px; }
.band-high .rv-score { background: var(--rv-high); }
.band-mid  .rv-score { background: var(--rv-mid); }
.band-low  .rv-score { background: var(--rv-low); }
.rv-body { padding: 14px 16px 12px; min-width: 0; }
.rv-body h3 { margin: 0; font-size: 1.05rem; font-weight: 600; line-height: 1.3; }
.rv-body h3 a { color: var(--rv-text) !important; text-decoration: none !important; }
.rv-body h3 a:hover { color: var(--rv-link); text-decoration: underline; }
.rv-meta { color: var(--rv-muted); margin-top: 3px; font-size: 0.85rem; color: var(--rv-muted); display: flex; flex-wrap: wrap; gap: 4px; }
.rv-company { font-weight: 600; color: var(--rv-text); }
.rv-dot { opacity: .5; }
.rv-reasoning { margin: 10px 0 0; font-size: 0.92rem; line-height: 1.5; color: var(--rv-text); }
.rv-details { margin-top: 8px; }
.rv-details summary { cursor: pointer; font-size: 0.82rem; color: var(--rv-link); font-weight: 500; list-style: none; }
.rv-details summary::-webkit-details-marker { display: none; }
.rv-details summary::before { content: "▸ "; }
.rv-details[open] summary::before { content: "▾ "; }
.rv-dims { list-style: none; padding: 0; margin: 10px 0 0; display: grid; gap: 10px; }
.rv-dim { padding: 10px 12px; border-radius: 8px; background: var(--rv-surface-2); color: var(--rv-text); }
.rv-dim-head { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; }
.rv-dim-score small { font-weight: 400; color: var(--rv-muted); }
.rv-dim-bar { height: 4px; border-radius: 2px; background: var(--rv-border); margin: 6px 0; overflow: hidden; }
.rv-dim-bar i { display: block; height: 100%; background: var(--rv-link); }
.rv-dim p { margin: 0; font-size: 0.85rem; color: var(--rv-muted); line-height: 1.45; }
.rv-actions {
  display: flex; align-items: center; gap: 14px; margin-top: 12px; padding-top: 10px;
  border-top: 1px solid var(--rv-border); font-size: 0.85rem;
}
.rv-tick { color: var(--rv-text); display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; }
.rv-tick input { width: 15px; height: 15px; accent-color: var(--rv-link); cursor: pointer; margin: 0; }
.rv-tick-applied input { accent-color: var(--rv-high); }
.rv-open { margin-left: auto; color: var(--rv-muted); text-decoration: none; }
.rv-open:hover { color: var(--rv-link); }

/* ---- clear ---- */
#rv-clear { align-items: center; gap: 12px; margin: 0 0 40px; padding-top: 12px; border-top: 1px dashed var(--rv-border); }
#rv-clear .prose, #rv-clear .prose * { color: var(--rv-muted); font-size: 0.85rem; }

/* ---- stars ---- */
.rv-rating { display: inline-flex; align-items: center; gap: 0; margin-left: 4px; }
.rv-star {
  background: none; border: none; padding: 0 1px; margin: 0; cursor: pointer;
  font-size: 1.05rem; line-height: 1; color: var(--rv-border); transition: color .1s;
}
.rv-star.on { color: #f59e0b; }
.rv-rating:hover .rv-star { color: var(--rv-border); }
.rv-rating .rv-star:hover, .rv-rating .rv-star:has(~ .rv-star:hover) { color: #f59e0b; }
.rv-rating-label { margin-left: 6px; font-size: 0.8rem; color: var(--rv-muted); min-width: 3.2em; }
.rv-query { color: var(--rv-muted); }

/* ---- queries table ---- */
.rv-table-wrap { overflow-x: auto; border: 1px solid var(--rv-border); border-radius: 12px; background: var(--rv-surface); }
.rv-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; color: var(--rv-text); }
.rv-table th { text-align: left; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--rv-muted); padding: 10px 12px; border-bottom: 1px solid var(--rv-border); white-space: nowrap; }
.rv-table td { padding: 10px 12px; border-bottom: 1px solid var(--rv-border); vertical-align: middle; }
.rv-table tr:last-child td { border-bottom: none; }
.rv-table td.num, .rv-table th:not(:first-child) { text-align: right; font-variant-numeric: tabular-nums; }
.rv-q-name { font-weight: 600; max-width: 380px; }
.rv-q-rating { white-space: nowrap; }
.rv-q-rating small { color: var(--rv-muted); }
.rv-q-bar { display: inline-block; width: 70px; height: 5px; border-radius: 3px; background: var(--rv-border); margin-right: 8px; overflow: hidden; vertical-align: middle; }
.rv-q-bar i { display: block; height: 100%; background: #f59e0b; }

/* ---- empty ---- */
.rv-empty {
  text-align: center; padding: 56px 20px; border: 1px dashed var(--rv-border);
  border-radius: 12px; color: var(--rv-muted);
}
.rv-empty h3 { margin: 0 0 6px; color: var(--rv-text); font-weight: 600; }
.rv-empty p { margin: 0; }

@media (max-width: 640px) {
  .rv-card { grid-template-columns: 56px 1fr; }
  .rv-score b { font-size: 1.2rem; }
  .rv-open { display: none; }
}
"""

# Event delegation on the HTML component's root: survives every re-render, and turns a
# native checkbox change into a Gradio `.click` event carrying {url, field, value}.
# The card's visual state flips locally so a tick feels instant; the server round-trip
# only persists it and refreshes the counters.
JS_ON_LOAD = """
element.addEventListener('click', (e) => {
  const star = e.target.closest('.rv-star');
  if (!star) return;
  const n = Number(star.dataset.value);
  const wrap = star.closest('.rv-rating');
  wrap.querySelectorAll('.rv-star').forEach(s => s.classList.toggle('on', Number(s.dataset.value) <= n));
  wrap.querySelector('.rv-rating-label').textContent = n + '/10';
  trigger('click', {url: star.dataset.url, field: 'rating', value: n});
});
element.addEventListener('change', (e) => {
  const box = e.target;
  if (!(box instanceof HTMLInputElement) || !box.dataset.field) return;
  const card = box.closest('.rv-card');
  if (card) card.classList.toggle('is-applied', box.checked);
  trigger('click', {url: box.dataset.url, field: box.dataset.field, value: box.checked});
});
"""
