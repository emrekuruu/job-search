from __future__ import annotations

import gradio as gr

theme = gr.themes.Default(
    primary_hue="indigo",
    secondary_hue="violet",
    neutral_hue="slate",
    radius_size=gr.themes.sizes.radius_lg,
    spacing_size=gr.themes.sizes.spacing_md,
    text_size=gr.themes.sizes.text_md,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "-apple-system", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"],
).set(
    # Subtle radial halo at the top of the page — light + dark variants.
    body_background_fill=(
        "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(99,102,241,0.08) 0%, "
        "transparent 60%), white"
    ),
    body_background_fill_dark=(
        "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(139,92,246,0.12) 0%, "
        "transparent 60%), rgb(11,11,14)"
    ),
    # Gradient CTA — primary button feels intentional.
    button_primary_background_fill=(
        "linear-gradient(90deg, var(--primary-500), var(--secondary-500))"
    ),
    button_primary_background_fill_hover=(
        "linear-gradient(90deg, var(--primary-600), var(--secondary-600))"
    ),
    button_primary_background_fill_dark=(
        "linear-gradient(90deg, var(--primary-500), var(--secondary-500))"
    ),
    button_primary_background_fill_hover_dark=(
        "linear-gradient(90deg, var(--primary-400), var(--secondary-400))"
    ),
    button_primary_text_color="white",
    button_primary_text_color_hover="white",
    # Softer block borders so cards/panels read as surfaces, not boxes.
    block_border_color="var(--neutral-200)",
    block_border_color_dark="var(--neutral-700)",
    block_border_width="1px",
    block_shadow="0 1px 2px rgba(0,0,0,0.03)",
)


CSS = """
/* ============================================================
   1. CONTAINER / LAYOUT
   ============================================================ */
.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 24px 16px 48px !important;
}

/* ============================================================
   2. #hero — gradient animated title + subtitle
   ============================================================ */
#hero {
    margin-bottom: 28px;
}
#hero h1 {
    font-size: 44px;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.1;
    margin: 0 0 6px 0;
    background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 45%, #ec4899 100%);
    background-size: 220% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: hue-shift 9s ease-in-out infinite;
}
#hero p {
    font-size: 16px;
    color: var(--body-text-color-subdued);
    margin: 0;
    line-height: 1.5;
    max-width: 640px;
}
@keyframes hue-shift {
    0%, 100% { background-position: 0% 50%; }
    50%     { background-position: 100% 50%; }
}

/* ============================================================
   3. .glass-panel — preferences panel with glassmorphism
   ============================================================ */
.glass-panel {
    background: color-mix(in srgb, var(--block-background-fill) 70%, transparent) !important;
    -webkit-backdrop-filter: blur(18px);
    backdrop-filter: blur(18px);
    border: 1px solid color-mix(in srgb, var(--primary-300) 35%, transparent) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.06);
    padding: 4px !important;
}
.glass-panel h3 {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.005em;
    margin: 4px 0 12px 0;
}

/* ============================================================
   4. Buttons — primary lift on hover
   ============================================================ */
button.primary {
    transition: transform 200ms ease-out, box-shadow 200ms ease-out;
    box-shadow: 0 4px 14px rgba(99,102,241,0.25);
    font-weight: 600;
    letter-spacing: -0.005em;
}
button.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(99,102,241,0.35);
}
button.primary:active {
    transform: translateY(0);
}

/* ============================================================
   4b. .start-over-row — right-aligned subtle back-link
   ============================================================ */
.start-over-row {
    justify-content: flex-end !important;
    margin: 4px 0 -8px 0;
}
.start-over-row button {
    background: transparent !important;
    border: 1px solid var(--border-color-primary) !important;
    color: var(--body-text-color-subdued) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 12px !important;
    border-radius: 999px !important;
    transition: all 180ms ease-out !important;
}
.start-over-row button:hover {
    border-color: color-mix(in srgb, var(--primary-500) 50%, transparent) !important;
    color: var(--primary-500) !important;
    background: color-mix(in srgb, var(--primary-500) 5%, transparent) !important;
}

/* ============================================================
   5. .stepper — circle + connector progress (Resume → Queries → Search → Evaluate)
   ============================================================ */
.stepper {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0;
    padding: 22px 28px 18px;
    background: color-mix(in srgb, var(--block-background-fill) 75%, transparent);
    -webkit-backdrop-filter: blur(10px);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg);
    margin: 16px 0;
}
.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    flex: 1;
    position: relative;
    min-width: 0;
}
.step-circle {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 700;
    transition: all 220ms ease-out;
    background: var(--block-background-fill);
    border: 2px solid var(--border-color-primary);
    color: var(--body-text-color-subdued);
    position: relative;
    z-index: 2;
}
.step::after {
    content: "";
    position: absolute;
    top: 19px;
    left: calc(50% + 24px);
    right: calc(-50% + 24px);
    height: 2px;
    background: var(--border-color-primary);
    z-index: 1;
    transition: background 280ms ease-out;
}
.step:last-child::after { display: none; }
.step.busy .step-circle {
    background: color-mix(in srgb, var(--primary-500) 12%, transparent);
    border-color: var(--primary-500);
    color: var(--primary-600);
    animation: pulse-glow 1.6s ease-in-out infinite;
}
.step.done .step-circle {
    background: linear-gradient(135deg, #10b981, #059669);
    border-color: transparent;
    color: white;
}
.step.done::after {
    background: linear-gradient(90deg, #10b981 0%, var(--border-color-primary) 100%);
}
.step-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: -0.005em;
    color: var(--body-text-color-subdued);
    transition: color 220ms ease-out;
}
.step.busy .step-label,
.step.done .step-label {
    color: var(--body-text-color);
}
.step-detail {
    font-size: 11px;
    color: var(--body-text-color-subdued);
    margin-top: -2px;
    height: 14px;
    line-height: 1;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--primary-500) 35%, transparent); }
    50%     { box-shadow: 0 0 0 8px color-mix(in srgb, var(--primary-500) 0%, transparent); }
}

/* ============================================================
   6. .job-card — accent strip + stagger fade + hover lift
   ============================================================ */
.job-card {
    position: relative;
    background: color-mix(in srgb, var(--block-background-fill) 78%, transparent);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg);
    padding: 18px 22px 18px 28px;
    margin-bottom: 14px;
    overflow: hidden;
    transition: transform 220ms ease-out, box-shadow 220ms ease-out, border-color 220ms ease-out;
    animation: fadein 280ms ease-out both;
}
.job-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
}
.card-accent {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--accent-from), var(--accent-to));
}
.job-card.score-high { --accent-from: #10b981; --accent-to: #059669; }
.job-card.score-mid  { --accent-from: #f59e0b; --accent-to: #d97706; }
.job-card.score-low  { --accent-from: #94a3b8; --accent-to: #64748b; }
.job-card h3 {
    margin: 0 0 4px 0;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
    line-height: 1.3;
    padding-right: 100px;
}
.job-card .meta {
    font-size: 13px;
    color: var(--body-text-color-subdued);
    margin-bottom: 10px;
}
.job-card .meta a {
    color: var(--primary-500);
    text-decoration: none;
    font-weight: 500;
}
.job-card .meta a:hover { text-decoration: underline; }
.job-card .overall {
    font-size: 14px;
    line-height: 1.55;
    margin-top: 8px;
}
@keyframes fadein {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ============================================================
   7. .score-badge — gradient pill, weight-700
   ============================================================ */
.score-badge {
    position: absolute;
    top: 18px;
    right: 22px;
    display: inline-flex;
    align-items: baseline;
    gap: 3px;
    padding: 6px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    color: white;
    box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    letter-spacing: -0.005em;
}
.score-badge small {
    font-weight: 500;
    opacity: 0.85;
    font-size: 11px;
}
.score-badge.score-high { background: linear-gradient(135deg, #10b981, #059669); }
.score-badge.score-mid  { background: linear-gradient(135deg, #f59e0b, #d97706); }
.score-badge.score-low  { background: linear-gradient(135deg, #94a3b8, #64748b); }

/* ============================================================
   8. .query-card — richer query view with metadata pills
   ============================================================ */
.query-card {
    background: color-mix(in srgb, var(--block-background-fill) 78%, transparent);
    -webkit-backdrop-filter: blur(10px);
    backdrop-filter: blur(10px);
    border: 1px solid color-mix(in srgb, var(--primary-400) 22%, transparent);
    border-radius: var(--radius-lg);
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: transform 200ms ease-out, box-shadow 200ms ease-out, border-color 200ms ease-out;
    animation: fadein 260ms ease-out both;
}
.query-card:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--primary-500) 42%, transparent);
    box-shadow: 0 6px 20px rgba(99,102,241,0.08);
}
.query-term {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.005em;
    color: var(--body-text-color);
    margin-bottom: 8px;
}
.query-term-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: linear-gradient(135deg, color-mix(in srgb, var(--primary-500) 22%, transparent), color-mix(in srgb, var(--secondary-500) 22%, transparent));
    font-size: 13px;
}
.query-term-text { flex: 1; }
.query-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.qpill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: color-mix(in srgb, var(--neutral-200) 35%, transparent);
    color: var(--body-text-color);
    border: 1px solid color-mix(in srgb, var(--neutral-300) 45%, transparent);
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 500;
}
.qpill-icon { font-size: 11px; line-height: 1; }
.qpill-remote {
    background: rgba(16,185,129,0.10);
    color: rgb(5,150,105);
    border-color: rgba(16,185,129,0.32);
}
.qpill-loc {
    background: color-mix(in srgb, var(--primary-500) 8%, transparent);
    color: var(--primary-600);
    border-color: color-mix(in srgb, var(--primary-500) 25%, transparent);
}

/* ============================================================
   8b. Inputs polish — segmented radios + upload zone
   ============================================================ */
.preference-radio > .block { padding: 0 !important; }
.preference-radio fieldset {
    border: none !important;
    padding: 0 !important;
    display: flex !important;
    flex-wrap: wrap;
    gap: 6px !important;
}
.preference-radio label {
    cursor: pointer !important;
    padding: 7px 14px !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-color-primary) !important;
    background: var(--block-background-fill) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--body-text-color) !important;
    transition: all 180ms ease-out !important;
    margin: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
}
.preference-radio label:hover {
    border-color: color-mix(in srgb, var(--primary-500) 55%, transparent) !important;
    background: color-mix(in srgb, var(--primary-500) 5%, transparent) !important;
}
.preference-radio input[type="radio"] {
    appearance: none !important;
    -webkit-appearance: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    position: absolute !important;
    opacity: 0 !important;
}
.preference-radio label:has(input:checked) {
    background: linear-gradient(135deg, var(--primary-500), var(--secondary-500)) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.30);
}

/* Upload zone — make the resume drop area feel intentional */
.upload-zone {
    border-radius: var(--radius-lg) !important;
}
.upload-zone .upload-container,
.upload-zone [data-testid="file"] {
    border: 2px dashed color-mix(in srgb, var(--primary-500) 32%, transparent) !important;
    border-radius: var(--radius-lg) !important;
    background: color-mix(in srgb, var(--primary-500) 4%, transparent) !important;
    transition: all 200ms ease-out !important;
}
.upload-zone:hover .upload-container,
.upload-zone:hover [data-testid="file"] {
    border-color: var(--primary-500) !important;
    background: color-mix(in srgb, var(--primary-500) 8%, transparent) !important;
}

/* ============================================================
   9. Dimension breakdown table
   ============================================================ */
details > summary {
    cursor: pointer;
    color: var(--primary-500);
    margin-top: 12px;
    font-size: 13px;
    font-weight: 500;
    user-select: none;
}
details[open] > summary { margin-bottom: 4px; }
.dim-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
    font-size: 13px;
}
.dim-table td {
    padding: 8px 8px;
    border-bottom: 1px solid var(--border-color-primary);
    vertical-align: top;
    line-height: 1.5;
}
.dim-table tr:last-child td { border-bottom: none; }
.dim-table .dim-name {
    font-weight: 600;
    width: 30%;
    color: var(--body-text-color);
}
.dim-table .dim-score {
    width: 11%;
    text-align: right;
    color: var(--primary-500);
    font-weight: 700;
}

/* ============================================================
   10. Tabs — clean underline indicator + dark-mode tweaks
   ============================================================ */
.tab-nav button {
    font-weight: 500 !important;
    transition: color 180ms ease, border-bottom-color 180ms ease;
}
.tab-nav button.selected {
    color: var(--primary-500) !important;
}

@media (prefers-color-scheme: dark) {
    .glass-panel {
        background: color-mix(in srgb, var(--block-background-fill) 55%, transparent) !important;
        border-color: color-mix(in srgb, var(--primary-400) 28%, transparent) !important;
    }
    .job-card:hover {
        box-shadow: 0 10px 28px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.22);
    }
    .pill-done {
        background: rgba(16,185,129,0.18);
        color: rgb(52,211,153);
    }
}
"""
