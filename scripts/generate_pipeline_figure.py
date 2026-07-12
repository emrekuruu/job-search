"""Generate the inference-pipeline figure for the blog post.

Aesthetic: Anthropic-inspired editorial / research-paper style.
  * Warm ivory canvas (#faf9f5), almost-achromatic warm-neutral palette.
  * Single terracotta accent (#d97757) for student-model nodes + stage numbers.
    Restrained per Anthropic's brand guidance: one accent per section maximum,
    default state uses zero chromatic color.
  * Sans-serif typography (Inter / Anthropic Sans / system) with tight tracking.
  * No shadows, no gradients, no decorative elements.

Pure-stdlib SVG synthesis. No matplotlib / no Tikz dependency.

Run:  uv run python scripts/generate_pipeline_figure.py
Out:  assets/figures/pipeline.svg
"""
from __future__ import annotations

from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "figures" / "pipeline.svg"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ====== canvas =================================================================
W, H = 1200, 300

# ====== palette (warm editorial, Anthropic-inspired) ===========================
CANVAS       = "#faf9f5"   # warm ivory parchment
STAGE_TINT   = "#f3f1ea"   # subtle parchment tint for stage groups
NODE_FILL    = "#ffffff"
BORDER_DATA  = "#e5e1d8"   # warm pale border (passive nodes)
BORDER_MODEL = "#d97757"   # warm terracotta border (student nodes)
ACCENT       = "#d97757"   # terracotta (stage number + model sub-label)
INK_900      = "#1a1815"   # warm near-black, primary text
INK_500      = "#6b6760"   # warm slate, secondary text + edge labels
INK_300      = "#aea99e"   # warm pale, arrows + dividers

# Inter first, then designer fallbacks, then system. Tight tracking is the
# defining typographic move in modern editorial design systems.
FONT = (
    '"Inter", "Söhne", "Anthropic Sans", "Helvetica Neue", Arial, '
    'system-ui, sans-serif'
)

# ====== stages =================================================================
STAGE_Y, STAGE_H = 55, 200
STAGES: list[tuple[float, float, str]] = [
    ( 30,  450, "01"),
    (480,  720, "02"),
    (750, 1170, "03"),
]

# ====== nodes ==================================================================
NODE_Y    = 155    # vertical centre line for all nodes
NODE_W    = 162
NODE_H    =  92
NODE_R    =  14    # corner radius

# (kind, primary label, secondary label, x_centre)
NODES: list[tuple[str, str, str, float]] = [
    ("data",  "Resume",             "PDF",            148),
    ("model", "Query Generation",   "Qwen3-8B",       354),
    ("data",  "Job search",         "via JobSpy",     600),
    ("model", "Listing Evaluation", "Qwen3-8B",       846),
    ("data",  "Ranked",             "Shortlist",     1064),
]

# Inter-node edge labels (empty string = no label on that edge).
EDGE_LABELS = ["", "queries", "jobs", "scores"]


# ============================================================================
# SVG synthesis
# ============================================================================
def header() -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {W} {H}" font-family={FONT!r} '
        'role="img" aria-label="End-to-end inference pipeline">',
        f'<rect width="{W}" height="{H}" fill="{CANVAS}" />',
        '<defs>'
        '<marker id="arrow" markerWidth="9" markerHeight="9" '
        'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
        f'<path d="M0,0 L0,6 L9,3 z" fill="{INK_300}" />'
        '</marker>'
        '</defs>',
    ]


def stages() -> list[str]:
    """Stage backgrounds with a single terracotta numeral at the top centre."""
    out: list[str] = []
    for x_a, x_b, num in STAGES:
        out.append(
            f'<rect x="{x_a}" y="{STAGE_Y}" width="{x_b - x_a}" '
            f'height="{STAGE_H}" rx="16" fill="{STAGE_TINT}" />'
        )
        cx = (x_a + x_b) / 2
        # Numeral only. The pipeline nodes carry the semantic meaning;
        # the stage rectangle does the visual grouping work.
        out.append(
            f'<text x="{cx}" y="{STAGE_Y + 26}" text-anchor="middle" '
            'font-size="11" font-weight="700" letter-spacing="0.18em" '
            f'fill="{ACCENT}">'
            f'{num}</text>'
        )
    return out


def edges() -> list[str]:
    """Thin horizontal arrows + italic edge labels between adjacent nodes."""
    out: list[str] = []
    for i in range(len(NODES) - 1):
        x_a = NODES[i][3] + NODE_W / 2 + 4
        x_b = NODES[i + 1][3] - NODE_W / 2 - 10  # leave room for the arrowhead
        out.append(
            f'<line x1="{x_a}" y1="{NODE_Y}" x2="{x_b}" y2="{NODE_Y}" '
            f'stroke="{INK_300}" stroke-width="1.2" marker-end="url(#arrow)" />'
        )
        label = EDGE_LABELS[i]
        if label:
            cx = (x_a + x_b) / 2
            out.append(
                f'<text x="{cx}" y="{NODE_Y - 10}" text-anchor="middle" '
                'font-size="10.5" font-style="italic" '
                f'fill="{INK_500}" letter-spacing="-0.005em">'
                f'{label}</text>'
            )
    return out


def nodes() -> list[str]:
    """Pipeline node cards (data vs model differentiated by border weight + accent)."""
    out: list[str] = []
    for kind, primary, secondary, x in NODES:
        x0 = x - NODE_W / 2
        y0 = NODE_Y - NODE_H / 2
        border = BORDER_MODEL if kind == "model" else BORDER_DATA
        sw = 1.6 if kind == "model" else 1.0
        out.append(
            f'<rect x="{x0}" y="{y0}" width="{NODE_W}" height="{NODE_H}" '
            f'rx="{NODE_R}" fill="{NODE_FILL}" '
            f'stroke="{border}" stroke-width="{sw}" />'
        )
        # Primary label — semibold near-black, tight track.
        # Font sized at 14 so the longer model labels ("Listing Evaluation",
        # "Query Generation") sit comfortably inside the box.
        out.append(
            f'<text x="{x}" y="{NODE_Y - 4}" text-anchor="middle" '
            'font-size="14" font-weight="600" letter-spacing="-0.01em" '
            f'fill="{INK_900}">'
            f'{primary}</text>'
        )
        # Secondary label — italic terracotta for the model name on student
        # nodes, warm slate roman for data nodes.
        italic = ' font-style="italic"' if kind == "model" else ""
        sec_fill = ACCENT if kind == "model" else INK_500
        out.append(
            f'<text x="{x}" y="{NODE_Y + 19}" text-anchor="middle" '
            f'font-size="11.5"{italic} fill="{sec_fill}" '
            'letter-spacing="-0.005em">'
            f'{secondary}</text>'
        )
    return out


def build() -> str:
    parts: list[str] = []
    parts += header()
    parts += stages()
    parts += edges()
    parts += nodes()
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


OUTPUT.write_text(build())
print(f"Wrote {OUTPUT.relative_to(Path.cwd())}  ({OUTPUT.stat().st_size} bytes)")
