"""collatro.render — Tailwind HTML card + Playwright screenshot (自適應高度)."""

from pathlib import Path

from src.config import TEMPLATES_DIR, OUTPUT_DIR

TEMPLATE = (TEMPLATES_DIR / "card.html").read_text(encoding="utf-8")

RECOMMENDED_THEMES = ["slate", "sky", "emerald", "amber", "violet", "rose"]

VERDICT_LABELS = {
    "match": ("text-green-400", "✓ 吻合"),
    "mismatch": ("text-red-400", "✗ 不一致"),
    "insufficient": ("text-yellow-400", "？ 證據不足"),
}


def _theme_classes(theme: str) -> dict:
    return {
        "bg_dark": f"{theme}-900",
        "bg_card": f"{theme}-800",
        "accent": f"{theme}-400",
        "text_muted": f"{theme}-400",
        "text_dim": f"{theme}-500",
        "border": f"{theme}-700",
    }


def _render_kg_tags(claim: dict) -> str:
    """Render Wikidata KG facts as tag pills."""
    enrich = claim.get("enrich", {})
    if not enrich:
        return ""
    tags = []
    # From wikidata structured facts
    wd = enrich.get("wikidata", {})
    for label, value in wd.items():
        if isinstance(value, list):
            value = "、".join(value[:2])
        tags.append(f'<span class="bg-cyan-500/20 text-cyan-300 text-xs px-2 py-1 rounded">{label}：{value}</span>')
    # Description as tag
    desc = enrich.get("description", "")
    if desc:
        tags.append(f'<span class="bg-slate-500/20 text-slate-300 text-xs px-2 py-1 rounded">{desc}</span>')
    if not tags:
        return ""
    return f'<div class="flex flex-wrap gap-2">{" ".join(tags[:6])}</div>'


def _render_section(items: list[dict], tag: str) -> str:
    if not items:
        return ""
    label_map = {
        "ner": ("NER", "bg-red-500/20 text-red-400"),
        "numbers": ("數字", "bg-amber-500/20 text-amber-400"),
        "timeline": ("時間", "bg-purple-500/20 text-purple-400"),
    }
    label, cls = label_map[tag]
    html = ""
    for item in items:
        html += f'''<div class="flex items-start gap-3">
      <span class="shrink-0 {cls} text-xs font-bold px-2 py-1 rounded">{label}</span>
      <div>
        <div class="text-sm"><span class="text-red-300">聲明：</span>{item.get("claim_says","")}</div>
        <div class="text-sm"><span class="text-green-300">證據：</span>{item.get("evidence_says","")}</div>
      </div>
    </div>\n'''
    return html


def _render_sources(evidence: list[dict]) -> str:
    if not evidence:
        return '<div class="text-sm text-slate-500">無搜尋結果</div>'
    html = ""
    for e in evidence[:4]:
        title = e.get("title", "")[:70]
        url = e.get("url", "")
        html += f'<div class="text-sm text-sky-300 truncate">🔗 {title}</div>\n'
        html += f'<div class="text-xs text-slate-500 truncate ml-5">{url}</div>\n'
    return html


def render_html(claim: dict, theme: str = "slate") -> str:
    """Render a single claim to HTML string."""
    diff = claim.get("diff", {})
    verdict = diff.get("verdict", "insufficient")
    color, label = VERDICT_LABELS.get(verdict, VERDICT_LABELS["insufficient"])
    tc = _theme_classes(theme)

    mismatches_html = _render_section(diff.get("ner", []), "ner")
    mismatches_html += _render_section(diff.get("numbers", []), "numbers")
    mismatches_html += _render_section(diff.get("timeline", []), "timeline")

    if not mismatches_html and verdict == "match":
        mismatches_html = '<div class="text-green-300 text-base py-4 text-center">所有事實與證據吻合 ✓</div>'
    elif not mismatches_html:
        mismatches_html = '<div class="text-yellow-300 text-base py-4 text-center">無具體差異可列出</div>'

    summary = diff.get("summary", "")
    if not summary or summary.startswith("{") or len(summary) > 80:
        summary = ""

    kg_html = _render_kg_tags(claim)

    html = TEMPLATE
    for key, val in tc.items():
        html = html.replace("{{" + key + "}}", val)
    html = html.replace("{{claim_text}}", claim.get("text", ""))
    html = html.replace("{{kg_tags}}", kg_html)
    html = html.replace("{{mismatches}}", mismatches_html)
    html = html.replace("{{verdict_color}}", color)
    html = html.replace("{{verdict_label}}", label)
    html = html.replace("{{summary}}", summary)
    html = html.replace("{{sources}}", _render_sources(claim.get("evidence", [])))
    return html


def render(claims: list[dict], theme: str = "slate") -> list[Path]:
    """Render all claims to 1080×auto PNG. Returns list of output paths."""
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(exist_ok=True)
    paths = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 800})

        for i, claim in enumerate(claims):
            html = render_html(claim, theme)
            page.set_content(html, wait_until="networkidle")
            # Auto-height: measure actual content height
            height = page.evaluate("document.querySelector('.card').offsetHeight")
            height = max(height, 400)  # minimum
            page.set_viewport_size({"width": 1080, "height": height})
            out_path = OUTPUT_DIR / f"claim_{i+1}.png"
            page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": 1080, "height": height})
            paths.append(out_path)

        browser.close()
    return paths
