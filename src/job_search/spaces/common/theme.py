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
    # Near-black base. The aurora layers sit on top of this in the fixed #aurora-bg
    # element rendered by ui.py — putting them in body_background_fill caused them to
    # not blur properly across rerenders.
    body_background_fill="#fafbff",
    body_background_fill_dark="#0a0b0f",
    # Gradient CTA — primary button feels intentional.
    button_primary_background_fill=(
        "linear-gradient(135deg, var(--primary-500), var(--secondary-500))"
    ),
    button_primary_background_fill_hover=(
        "linear-gradient(135deg, var(--primary-600), var(--secondary-500))"
    ),
    button_primary_background_fill_dark=(
        "linear-gradient(135deg, var(--primary-500), var(--secondary-500))"
    ),
    button_primary_background_fill_hover_dark=(
        "linear-gradient(135deg, var(--primary-400), var(--secondary-400))"
    ),
    button_primary_text_color="white",
    button_primary_text_color_hover="white",
    # Softer block borders so cards/panels read as surfaces, not boxes.
    block_border_color="var(--neutral-200)",
    block_border_color_dark="rgba(255,255,255,0.06)",
    block_border_width="1px",
    block_shadow="0 1px 2px rgba(0,0,0,0.03)",
)


CSS = """
/* ============================================================
   0. ROOT LAYERING + NEAR-BLACK BG
   ============================================================ */
html, body {
    background: #0a0b0f !important;
}
.gradio-container, .main, .contain {
    position: relative;
    z-index: 1;
}

/* ============================================================
   0b. NUKE EVERY FOCUS OUTLINE + CONTAINER BORDER GRADIO ADDS
   ============================================================
   Gradio + the browser apply a default 2px focus outline on focused/active
   containers (Accordion, Markdown, Column wrappers). That outline picks up the
   theme's primary color and renders as a bright purple rectangle. Kill it across
   every state, plus strip default container borders we don't want. */
*, *:focus, *:focus-visible, *:focus-within, *:hover, *:active {
    outline: none !important;
    outline-offset: 0 !important;
}
.gradio-container .block,
.gradio-container .form,
.gradio-container .gr-form,
.gradio-container .gr-block,
.gradio-container .container,
.gradio-container .wrap,
.gradio-container [class*="container"]:not(.gradio-container):not([class*="upload"]),
.gradio-container [class*="block"]:not(button) {
    border: none !important;
    outline: none !important;
}
/* Specific kill for the results section and its descendants — that's the area
   that was showing the bright purple rectangle around the stepper + tabs. */
.results-section,
.results-section *,
.inputs-section,
.inputs-section *:not(button):not(label):not(.preference-radio label) {
    border: none !important;
    outline: none !important;
}

/* ============================================================
   1. AURORA BACKGROUND — 3 soft color blobs + slow rotation.
      Rendered by ui.py as <div id="aurora-bg">; pinned behind everything.
   ============================================================ */
#aurora-bg {
    position: fixed;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 0;
}
.aurora-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.55;
    will-change: transform;
}
.aurora-1 {
    width: 620px;
    height: 620px;
    top: -180px;
    left: -120px;
    background: radial-gradient(circle at 50% 50%, #6366f1 0%, transparent 70%);
    animation: aurora-drift-1 22s ease-in-out infinite;
}
.aurora-2 {
    width: 560px;
    height: 560px;
    top: -140px;
    right: -140px;
    background: radial-gradient(circle at 50% 50%, #a855f7 0%, transparent 70%);
    animation: aurora-drift-2 28s ease-in-out infinite;
}
.aurora-3 {
    width: 720px;
    height: 720px;
    bottom: -260px;
    left: 30%;
    background: radial-gradient(circle at 50% 50%, #06b6d4 0%, transparent 70%);
    opacity: 0.32;
    animation: aurora-drift-3 36s ease-in-out infinite;
}
@keyframes aurora-drift-1 {
    0%, 100% { transform: translate(0, 0); }
    50%      { transform: translate(60px, 40px); }
}
@keyframes aurora-drift-2 {
    0%, 100% { transform: translate(0, 0); }
    50%      { transform: translate(-40px, 80px); }
}
@keyframes aurora-drift-3 {
    0%, 100% { transform: translate(0, 0); }
    50%      { transform: translate(40px, -50px); }
}
/* Faint grain for premium feel */
#aurora-bg::after {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        radial-gradient(rgba(255,255,255,0.025) 1px, transparent 1px);
    background-size: 3px 3px;
    opacity: 0.4;
}

/* Light-mode auroras: pull saturation down so things stay legible */
@media (prefers-color-scheme: light) {
    html, body { background: #fafbff !important; }
    .aurora-blob { opacity: 0.30; }
    .aurora-3 { opacity: 0.18; }
}

/* ============================================================
   2. CONTAINER / LAYOUT
   ============================================================ */
.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 32px 16px 64px !important;
}

/* ============================================================
   3. #hero — kicker + iridescent display H1 + subtitle
   ============================================================ */
#hero {
    margin-bottom: 36px;
    animation: fadein 320ms ease-out both;
}
.hero-kicker {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--body-text-color) 55%, transparent);
    margin: 0 0 14px 0;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}
.hero-kicker::before {
    content: "";
    width: 22px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--primary-400));
}
.hero-kicker::after {
    content: "";
    width: 22px;
    height: 1px;
    background: linear-gradient(90deg, var(--primary-400), transparent);
}
#hero h1 {
    font-size: 56px;
    font-weight: 600;
    letter-spacing: -0.04em;
    line-height: 0.95;
    margin: 0 0 14px 0;
    background: linear-gradient(120deg,
        #6366f1 0%,
        #8b5cf6 28%,
        #ec4899 58%,
        #06b6d4 85%,
        #6366f1 100%);
    background-size: 280% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: hue-shift 14s ease-in-out infinite;
}
#hero p {
    font-size: 16px;
    color: color-mix(in srgb, var(--body-text-color) 70%, transparent);
    margin: 0;
    line-height: 1.55;
    max-width: 600px;
}
@keyframes hue-shift {
    0%, 100% { background-position: 0% 50%; }
    50%      { background-position: 100% 50%; }
}

/* ============================================================
   4. .glass-panel — heavy glassmorphism for the preferences card
   ============================================================ */
.glass-panel {
    background: color-mix(in srgb, var(--block-background-fill) 12%, transparent) !important;
    -webkit-backdrop-filter: blur(28px) saturate(140%);
    backdrop-filter: blur(28px) saturate(140%);
    /* Borderless: any border would refract the aurora and read as a purple/lavender rim.
       The panel is defined purely by the bg tint vs. the page. */
    border: none !important;
    outline: none !important;
    border-radius: 20px !important;
    box-shadow: none !important;
    padding: 48px 32px 32px 32px !important;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 18px;
}
@media (prefers-color-scheme: light) {
    .glass-panel {
        background: color-mix(in srgb, white 70%, transparent) !important;
    }
}
.glass-panel > .panel-heading,
.glass-panel > div > .panel-heading {
    display: none !important;  /* "What kind of role are you after?" header — drop the marketing label */
}

/* CRITICAL: strip every nested Gradio wrapper inside .glass-panel so we don't see a
   "panel within a panel" effect. Gradio wraps gr.Group / gr.Column in their own divs
   with default bg + border + border-radius + box-shadow + background-image. We nuke
   ALL of those on every descendant div that isn't one of our own classes. */
.glass-panel div:not(.preference-section):not(.section-divider):not(.section-label):not(.preference-radio):not([role="radiogroup"]):not(.wrap) {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
.glass-panel > div,
.glass-panel > div > div,
.glass-panel .block,
.glass-panel .form,
.glass-panel .gr-form,
.glass-panel .gr-block,
.glass-panel .gradio-group,
.glass-panel > .gr-group {
    padding: 0 !important;
}
/* Preserve the column/row gap so sections don't squish together */
.glass-panel > div { display: flex; flex-direction: column; gap: 18px; }

/* Belt-and-suspenders: explicit top margin on the FIRST section so JOB TYPE sits
   well below the panel's top edge regardless of which inner wrapper is present. */
.glass-panel .preference-section:first-of-type,
.glass-panel > div > .preference-section:first-of-type,
.glass-panel > div > div > .preference-section:first-of-type {
    margin-top: 12px;
}

/* ============================================================
   5. .preference-section — micro-label + content stack
   ============================================================ */
.preference-section { gap: 6px !important; }

/* Our own mono uppercase label, emitted as <div class="section-label"> from ui.py.
   We don't try to restyle Gradio's built-in labels because the DOM moves on us. */
.section-label {
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--body-text-color) 50%, transparent);
    margin-bottom: 6px;
    text-align: center;
}

/* Hairline separator between preference sections */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg,
        transparent,
        color-mix(in srgb, var(--body-text-color) 10%, transparent) 20%,
        color-mix(in srgb, var(--body-text-color) 10%, transparent) 80%,
        transparent);
    margin: 6px 0 2px 0;
    border: none !important;
}

/* ============================================================
   6. .inputs-section — staggered fade-in
   ============================================================ */
.inputs-section {
    animation: fadein 360ms ease-out both;
    animation-delay: 80ms;
}

/* ============================================================
   7. Buttons + CTA — content-width, subtle glow on hover only
   ============================================================ */
.submit-row {
    justify-content: center !important;
    margin-top: 20px;
}
.submit-cta {
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
    flex: 0 0 auto !important;
    padding: 11px 28px !important;
    font-size: 14.5px !important;
    font-weight: 600 !important;
    letter-spacing: -0.005em !important;
    border-radius: 12px !important;
    border: none !important;
    position: relative;
    box-shadow: 0 1px 2px rgba(0,0,0,0.25) !important;
    transition: transform 180ms ease-out, box-shadow 220ms ease-out, filter 200ms ease-out !important;
}
.submit-cta::after {
    content: "  →";
    opacity: 0.85;
    display: inline-block;
    transition: transform 180ms ease-out;
}
.submit-cta:hover {
    transform: translateY(-1px) !important;
    box-shadow:
        0 0 20px rgba(139,92,246,0.35),
        0 2px 6px rgba(0,0,0,0.30) !important;
    filter: brightness(1.05);
}
.submit-cta:hover::after {
    transform: translateX(3px);
}
.submit-cta:active {
    transform: translateY(0) !important;
    filter: brightness(0.98);
}

/* Generic primary lift fallback */
button.primary {
    transition: transform 200ms ease-out, box-shadow 200ms ease-out;
    font-weight: 600;
    letter-spacing: -0.005em;
}

/* ============================================================
   7b. .start-over-row — right-aligned subtle back-link
   ============================================================ */
.start-over-row {
    justify-content: flex-end !important;
    margin: 4px 0 -8px 0;
}
.start-over-row button {
    background: color-mix(in srgb, var(--body-text-color) 6%, transparent) !important;
    border: none !important;
    color: color-mix(in srgb, var(--body-text-color) 65%, transparent) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 12px !important;
    border-radius: 999px !important;
    transition: all 180ms ease-out !important;
}
.start-over-row button:hover {
    color: var(--primary-400) !important;
    background: color-mix(in srgb, var(--primary-500) 12%, transparent) !important;
}

/* ============================================================
   8. Segmented preference radios — tighter pills, smoother check
   ============================================================ */
.preference-radio > .block { padding: 0 !important; }
/* Gradio's Radio DOM varies by version: <fieldset>, [role=radiogroup], or .wrap div.
   Target all three so centering actually applies. */
.preference-radio fieldset,
.preference-radio [role="radiogroup"],
.preference-radio .wrap,
.preference-radio > .gr-form > div,
.preference-radio > div > div {
    border: none !important;
    padding: 0 !important;
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    justify-content: center !important;  /* center pills horizontally in the panel */
    align-items: center !important;
}
.preference-radio label {
    cursor: pointer !important;
    padding: 7px 14px !important;
    border-radius: 10px !important;
    border: none !important;
    background: color-mix(in srgb, var(--body-text-color) 6%, transparent) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    color: color-mix(in srgb, var(--body-text-color) 75%, transparent) !important;
    transition: all 220ms ease-out !important;
    margin: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
}
.preference-radio label:hover {
    background: color-mix(in srgb, var(--primary-500) 12%, transparent) !important;
    color: var(--body-text-color) !important;
}
.preference-radio input[type="radio"] {
    appearance: none !important;
    -webkit-appearance: none !important;
    width: 0 !important; height: 0 !important;
    margin: 0 !important; padding: 0 !important;
    border: none !important; position: absolute !important; opacity: 0 !important;
}
.preference-radio label:has(input:checked) {
    background: linear-gradient(135deg, var(--primary-500), var(--secondary-500)) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.15),
        0 2px 8px rgba(99,102,241,0.30);
}

/* ============================================================
   9. Upload zone — glass surface that matches the preferences panel
   ============================================================ */
.upload-column {
    display: flex !important;
    flex-direction: column;
    gap: 6px;
    height: 100%;
}
.upload-column > div:last-child { flex: 1 1 auto; display: flex; }
.upload-zone {
    border-radius: 20px !important;
    height: 100% !important;
    flex: 1 1 auto !important;
}
.upload-zone > .block,
.upload-zone > div {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    height: 100% !important;
}
/* Empty drop area — same glass treatment as .glass-panel: bg 12%, blur 28px,
   saturate 140%, radius 20px. So the left and right columns read as the same
   surface vocabulary. */
.upload-zone .upload-container,
.upload-zone [data-testid="file"] {
    border: none !important;
    border-radius: 20px !important;
    background: color-mix(in srgb, var(--block-background-fill) 12%, transparent) !important;
    -webkit-backdrop-filter: blur(28px) saturate(140%);
    backdrop-filter: blur(28px) saturate(140%);
    transition: background 220ms ease-out !important;
    height: 100% !important;
    min-height: 220px !important;
    padding: 32px 24px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 18px !important;  /* breathing room between icon and the drop text */
}
.upload-zone:hover .upload-container,
.upload-zone:hover [data-testid="file"] {
    background: color-mix(in srgb, var(--primary-500) 8%, transparent) !important;
}
/* Force inner Gradio drop wrapper to also center + space its children */
.upload-zone .wrap,
.upload-zone .upload-container > *,
.upload-zone [data-testid="file"] > * {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 14px !important;
    width: 100% !important;
    text-align: center !important;
}
.upload-zone svg {
    color: var(--primary-400) !important;
    width: 32px !important;
    height: 32px !important;
    display: block !important;
    margin: 0 auto !important;
}
/* Compact wording: hide "- or -" separator, tighten lines */
.upload-zone .wrap p,
.upload-zone .wrap span,
.upload-zone span[data-testid="hint"] {
    font-size: 13px !important;
    color: color-mix(in srgb, var(--body-text-color) 55%, transparent) !important;
    font-weight: 500 !important;
    margin: 0 !important;
    line-height: 1.4 !important;
}
.upload-zone .wrap p:first-of-type {
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: -0.005em !important;
    color: color-mix(in srgb, var(--body-text-color) 88%, transparent) !important;
}
/* Drop the "- or -" middle line entirely */
.upload-zone .wrap *:nth-child(3),
.upload-zone .or-text {
    display: none !important;
}
/* Filled state — file pill, borderless */
.upload-zone .file-preview,
.upload-zone .selected-file,
.upload-zone [data-testid="file-component"] {
    background: color-mix(in srgb, var(--body-text-color) 6%, transparent) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 13px !important;
    min-height: 0 !important;
}

/* ============================================================
   10. Inputs (textbox / textarea) — centered, bottom-rule pattern
   ============================================================ */

/* Strip EVERY Gradio container layer around the textbox/textarea so only the
   bare input + our single bottom rule remains. The "messy underline" below the
   Anything-else textarea was Gradio's own wrapper showing residual borders/footers. */
.preference-section .form,
.preference-section .form-wrap,
.preference-section .form > *,
.preference-section .block,
.preference-section .block > *,
.preference-section .container,
.preference-section .wrap,
.preference-section .gradio-textbox,
.preference-section .gradio-textbox > *,
.preference-section [class*="textbox"],
.preference-section [class*="textbox"] > * {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
/* Hide any empty label / footer slot that still claims vertical space */
.preference-section .label-wrap:empty,
.preference-section .block-info:empty,
.preference-section .footer:empty,
.preference-section > .form > label[for] {
    display: none !important;
}

.preference-section input[type="text"],
.preference-section textarea,
.glass-panel input[type="text"],
.glass-panel textarea {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 8px 2px !important;
    font-size: 14px !important;
    color: var(--body-text-color) !important;
    box-shadow: none !important;
    text-align: center !important;  /* center the input value + placeholder */
    width: 100% !important;
    display: block !important;
    margin: 0 !important;
    transition: color 180ms ease-out !important;
}
.preference-section input[type="text"]::placeholder,
.preference-section textarea::placeholder,
.glass-panel input[type="text"]::placeholder,
.glass-panel textarea::placeholder {
    color: color-mix(in srgb, var(--body-text-color) 30%, transparent) !important;
    font-weight: 400 !important;
    text-align: center !important;
}
.preference-section input[type="text"]:focus,
.preference-section textarea:focus,
.glass-panel input[type="text"]:focus,
.glass-panel textarea:focus {
    outline: none !important;
    box-shadow: none !important;
}
.preference-section textarea,
.glass-panel textarea {
    resize: none !important;
    line-height: 1.55 !important;
    text-align: center !important;
}

/* ============================================================
   11. .stepper — circle + connector progress
   ============================================================ */
.stepper {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0;
    padding: 22px 28px 18px;
    background: color-mix(in srgb, var(--block-background-fill) 12%, transparent);
    -webkit-backdrop-filter: blur(24px) saturate(140%);
    backdrop-filter: blur(24px) saturate(140%);
    border: none;
    border-radius: 18px;
    margin: 16px 0;
    box-shadow: none;
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
    width: 38px; height: 38px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700;
    transition: all 220ms ease-out;
    background: color-mix(in srgb, var(--body-text-color) 10%, transparent);
    border: none;
    color: color-mix(in srgb, var(--body-text-color) 55%, transparent);
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
    background: color-mix(in srgb, var(--body-text-color) 14%, transparent);
    z-index: 1;
    transition: background 280ms ease-out;
}
.step:last-child::after { display: none; }
.step.busy .step-circle {
    background: color-mix(in srgb, var(--primary-500) 24%, transparent);
    color: var(--primary-300);
    animation: pulse-glow 1.6s ease-in-out infinite;
}
.step.done .step-circle {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
}
.step.done::after {
    background: linear-gradient(90deg, #10b981 0%, color-mix(in srgb, var(--body-text-color) 14%, transparent) 100%);
}
.step-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--body-text-color) 55%, transparent);
    transition: color 220ms ease-out;
}
.step.busy .step-label,
.step.done .step-label {
    color: var(--body-text-color);
}
.step-detail {
    font-size: 11px;
    color: color-mix(in srgb, var(--body-text-color) 60%, transparent);
    margin-top: -2px;
    height: 14px;
    line-height: 1;
    font-family: var(--font-mono);
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--primary-500) 35%, transparent); }
    50%     { box-shadow: 0 0 0 8px color-mix(in srgb, var(--primary-500) 0%, transparent); }
}

/* ============================================================
   12. .job-card — accent strip + fadein + hover lift
   ============================================================ */
.job-card {
    position: relative;
    background: color-mix(in srgb, var(--block-background-fill) 14%, transparent);
    -webkit-backdrop-filter: blur(24px) saturate(140%);
    backdrop-filter: blur(24px) saturate(140%);
    border: none;
    border-radius: 18px;
    padding: 20px 24px 20px 30px;
    margin-bottom: 14px;
    overflow: hidden;
    transition: transform 220ms ease-out, background 220ms ease-out;
    animation: fadein 280ms ease-out both;
    box-shadow: none;
}
.job-card:hover {
    transform: translateY(-2px);
    background: color-mix(in srgb, var(--block-background-fill) 20%, transparent);
}
.card-accent {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--accent-from), var(--accent-to));
}
.job-card.score-green  { --accent-from: #10b981; --accent-to: #059669; }
.job-card.score-yellow { --accent-from: #eab308; --accent-to: #ca8a04; }
.job-card.score-orange { --accent-from: #f97316; --accent-to: #ea580c; }
.job-card.score-red    { --accent-from: #ef4444; --accent-to: #dc2626; }
.job-card.score-streaming { --accent-from: var(--primary-500); --accent-to: var(--secondary-500); }
.job-card h3 {
    margin: 0 0 4px 0;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.015em;
    line-height: 1.3;
    padding-right: 100px;
}
.job-card .meta {
    font-size: 13px;
    color: color-mix(in srgb, var(--body-text-color) 65%, transparent);
    margin-bottom: 10px;
}
.job-card .meta a {
    color: var(--primary-400);
    text-decoration: none;
    font-weight: 500;
}
.job-card .meta a:hover { text-decoration: underline; }
.job-card .overall {
    font-size: 14px;
    line-height: 1.6;
    margin-top: 8px;
}
@keyframes fadein {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Streaming card (skeleton while reasoning fills) */
.streaming-reasoning {
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.7;
    color: color-mix(in srgb, var(--body-text-color) 75%, transparent);
    background: color-mix(in srgb, var(--primary-500) 6%, transparent);
    border-left: 2px solid color-mix(in srgb, var(--primary-400) 50%, transparent);
    padding: 10px 14px;
    border-radius: 0 12px 12px 0;
    margin-top: 10px;
    white-space: pre-wrap;
    max-height: 160px;
    overflow-y: auto;
}
.streaming-dots {
    display: inline-block;
    animation: streaming-blink 1.4s ease-in-out infinite;
}
@keyframes streaming-blink {
    0%, 100% { opacity: 0.35; }
    50%      { opacity: 1; }
}

/* ============================================================
   13. .score-badge — gradient pill, weight-700
   ============================================================ */
.score-badge {
    position: absolute;
    top: 20px;
    right: 22px;
    display: inline-flex;
    align-items: baseline;
    gap: 3px;
    padding: 6px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    color: white;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.18),
        0 2px 10px rgba(0,0,0,0.18);
    letter-spacing: -0.005em;
}
.score-badge small {
    font-weight: 500;
    opacity: 0.85;
    font-size: 11px;
}
.score-badge.score-green  { background: linear-gradient(135deg, #10b981, #059669); }
.score-badge.score-yellow { background: linear-gradient(135deg, #eab308, #ca8a04); }
.score-badge.score-orange { background: linear-gradient(135deg, #f97316, #ea580c); }
.score-badge.score-red    { background: linear-gradient(135deg, #ef4444, #dc2626); }
.score-badge.score-streaming {
    background: linear-gradient(135deg, var(--primary-500), var(--secondary-500));
    animation: streaming-blink 1.4s ease-in-out infinite;
}

/* ============================================================
   14. .query-card — query view with metadata pills
   ============================================================ */
.query-card {
    background: color-mix(in srgb, var(--block-background-fill) 12%, transparent);
    -webkit-backdrop-filter: blur(20px) saturate(140%);
    backdrop-filter: blur(20px) saturate(140%);
    border: none;
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: transform 200ms ease-out, background 200ms ease-out;
    animation: fadein 260ms ease-out both;
    box-shadow: none;
}
.query-card:hover {
    transform: translateY(-1px);
    background: color-mix(in srgb, var(--primary-500) 8%, transparent);
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
    align-items: center; justify-content: center;
    width: 24px; height: 24px;
    border-radius: 8px;
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--primary-500) 22%, transparent),
        color-mix(in srgb, var(--secondary-500) 22%, transparent));
    font-size: 13px;
}
.query-term-text { flex: 1; }
.query-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.qpill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: color-mix(in srgb, var(--body-text-color) 8%, transparent);
    color: var(--body-text-color);
    border: none;
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 500;
}
.qpill-icon { font-size: 11px; line-height: 1; }
.qpill-remote {
    background: rgba(16,185,129,0.16);
    color: rgb(52,211,153);
}
.qpill-loc {
    background: color-mix(in srgb, var(--primary-500) 14%, transparent);
    color: var(--primary-300);
}

/* ============================================================
   15. .main-tabs — underline indicator with gradient
   ============================================================ */
.main-tabs .tab-nav {
    gap: 4px !important;
    border: none !important;
    margin-bottom: 16px;
}
.main-tabs .tab-nav button {
    background: transparent !important;
    border: none !important;
    color: color-mix(in srgb, var(--body-text-color) 55%, transparent) !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    letter-spacing: -0.005em !important;
    padding: 10px 18px !important;
    transition: all 200ms ease-out !important;
    position: relative;
}
.main-tabs .tab-nav button:hover {
    color: var(--body-text-color) !important;
}
.main-tabs .tab-nav button.selected {
    color: var(--body-text-color) !important;
    font-weight: 600 !important;
}
.main-tabs .tab-nav button.selected::after {
    content: "";
    position: absolute;
    left: 18px; right: 18px; bottom: -1px;
    height: 2px;
    background: linear-gradient(90deg, var(--primary-500), var(--secondary-500));
    border-radius: 2px;
}

/* ============================================================
   16. Reasoning accordion — quote-card with left accent
   ============================================================ */
.reasoning-accordion {
    border: none !important;
    border-radius: 16px !important;
    background: color-mix(in srgb, var(--block-background-fill) 8%, transparent) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
    margin-top: 14px !important;
}
.reasoning-accordion > .label-wrap,
.reasoning-accordion > button {
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: -0.005em !important;
    color: var(--body-text-color) !important;
    padding: 12px 16px !important;
}
.reasoning-accordion > .label-wrap::before,
.reasoning-accordion > button::before {
    content: "💭 ";
    margin-right: 4px;
    opacity: 0.7;
}
.reasoning-content {
    background: color-mix(in srgb, var(--primary-500) 8%, transparent) !important;
    border: none !important;
    border-radius: 12px;
    padding: 16px 20px !important;
    margin: 8px 12px 12px 12px !important;
    font-size: 13px !important;
    line-height: 1.75 !important;
    color: var(--body-text-color);
    font-family: var(--font-mono) !important;
}
.reasoning-content p { margin: 0 0 12px 0 !important; }
.reasoning-content p:last-child { margin-bottom: 0 !important; }
.reasoning-content strong {
    color: var(--primary-400);
    font-weight: 600;
}

/* ============================================================
   17. Dimension breakdown table
   ============================================================ */
details > summary {
    cursor: pointer;
    color: var(--primary-400);
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
    padding: 10px 8px;
    border: none;
    vertical-align: top;
    line-height: 1.5;
}
.dim-table tr:nth-child(even) td {
    background: color-mix(in srgb, var(--body-text-color) 4%, transparent);
}
.dim-table .dim-name {
    font-weight: 600;
    width: 30%;
    color: var(--body-text-color);
}
.dim-table .dim-score {
    width: 11%;
    text-align: right;
    color: var(--primary-400);
    font-weight: 700;
    font-family: var(--font-mono);
}

/* ============================================================
   19. Results viewer — reviewed/applied state + profile gate
   ============================================================ */
.status-pill {
    display: inline-block;
    margin-left: 10px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    vertical-align: middle;
    text-transform: uppercase;
}
.status-pill.status-reviewed {
    background: color-mix(in srgb, var(--primary-500) 22%, transparent);
    color: var(--primary-300);
}
.status-pill.status-applied {
    background: linear-gradient(135deg, #10b981, #059669);
    color: #fff;
}
/* Ticked cards recede so unhandled matches read first. */
.job-card.card-done { opacity: 0.55; }
.job-card.card-done:hover { opacity: 1; }

.job-row-actions {
    display: flex;
    gap: 18px;
    align-items: center;
    padding: 0 24px 16px 30px;
    margin-top: -8px;
}
.profile-gate {
    max-width: 460px;
    margin: 0 auto;
    text-align: center;
}
"""
