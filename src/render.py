"""collatro.render — 三種獨立格式的圖卡生成（橫式 / Reels / Square）."""

from pathlib import Path
from src.config import TEMPLATES_DIR, OUTPUT_DIR

TEMPLATE = (TEMPLATES_DIR / "card.html").read_text(encoding="utf-8")
TEMPLATE_REELS = (TEMPLATES_DIR / "card_reels.html").read_text(encoding="utf-8")
TEMPLATE_SQUARE = (TEMPLATES_DIR / "card_square.html").read_text(encoding="utf-8")

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
    enrich = claim.get("enrich", {})
    if not enrich:
        return ""
    tags = []
    wd = enrich.get("wikidata", {})
    for label, value in wd.items():
        if isinstance(value, list):
            value = "、".join(value[:2])
        tags.append(f'<span class="bg-cyan-500/20 text-cyan-300 text-xs px-2 py-1 rounded">{label}：{value}</span>')
    desc = enrich.get("description", "")
    if desc:
        tags.append(f'<span class="bg-slate-500/20 text-slate-300 text-xs px-2 py-1 rounded">{desc}</span>')
    if not tags:
        return ""
    return f'<div class="flex flex-wrap gap-2">{" ".join(tags[:6])}</div>'


def _render_diff_section(items: list[dict], tag: str) -> str:
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


def _get_verdict(diff: dict) -> tuple[str, str]:
    verdict = diff.get("verdict", "insufficient")
    return VERDICT_LABELS.get(verdict, VERDICT_LABELS["insufficient"])


def _get_summary(diff: dict) -> str:
    summary = diff.get("summary", "")
    if not summary or summary.startswith("{") or len(summary) > 120:
        return ""
    return summary


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 橫式 (1080×auto) — 完整版：聲明 + verdict + 差異 + 來源
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_html_wide(claim: dict, theme: str = "slate") -> str:
    diff = claim.get("diff", {})
    color, label = _get_verdict(diff)
    tc = _theme_classes(theme)

    mismatches = _render_diff_section(diff.get("ner", []), "ner")
    mismatches += _render_diff_section(diff.get("numbers", []), "numbers")
    mismatches += _render_diff_section(diff.get("timeline", []), "timeline")
    if not mismatches:
        v = diff.get("verdict", "insufficient")
        if v == "match":
            mismatches = '<div class="text-green-300 text-base py-4 text-center">所有事實與證據吻合 ✓</div>'
        else:
            mismatches = '<div class="text-yellow-300 text-base py-4 text-center">無具體差異可列出</div>'

    html = TEMPLATE
    for key, val in tc.items():
        html = html.replace("{{" + key + "}}", val)
    html = html.replace("{{claim_text}}", claim.get("text", ""))
    html = html.replace("{{kg_tags}}", _render_kg_tags(claim))
    html = html.replace("{{mismatches}}", mismatches)
    html = html.replace("{{verdict_color}}", color)
    html = html.replace("{{verdict_label}}", label)
    html = html.replace("{{summary}}", _get_summary(diff))
    html = html.replace("{{sources}}", _render_sources(claim.get("evidence", [])))
    return html


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reels (1080×1920) — 重點版：聲明 + verdict + summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_html_reels(claim: dict, theme: str = "slate", font_scale: float = 1.0) -> str:
    diff = claim.get("diff", {})
    color, label = _get_verdict(diff)
    tc = _theme_classes(theme)

    html = TEMPLATE_REELS
    for key, val in tc.items():
        html = html.replace("{{" + key + "}}", val)
    html = html.replace("{{claim_text}}", claim.get("text", ""))
    html = html.replace("{{verdict_color}}", color)
    html = html.replace("{{verdict_label}}", label)
    html = html.replace("{{summary}}", _get_summary(diff))
    html = html.replace("{{font_scale}}", f"{font_scale:.2f}")
    return html


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Square (1080×1080) — 精簡版：聲明 + verdict
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_html_square(claim: dict, theme: str = "slate", font_scale: float = 1.0) -> str:
    diff = claim.get("diff", {})
    color, label = _get_verdict(diff)
    tc = _theme_classes(theme)

    html = TEMPLATE_SQUARE
    for key, val in tc.items():
        html = html.replace("{{" + key + "}}", val)
    html = html.replace("{{claim_text}}", claim.get("text", ""))
    html = html.replace("{{verdict_color}}", color)
    html = html.replace("{{verdict_label}}", label)
    html = html.replace("{{summary}}", _get_summary(diff))
    html = html.replace("{{font_scale}}", f"{font_scale:.2f}")
    return html


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 自適應 scale（用於固定尺寸格式）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _find_best_scale(page, render_fn, claim, theme, container_h, max_scale=2.5):
    """Binary search for max scale that fits container."""
    lo, hi = 1.0, max_scale
    for _ in range(6):
        mid = (lo + hi) / 2
        html = render_fn(claim, theme, font_scale=mid)
        page.set_content(html, wait_until="networkidle")
        h = page.evaluate("""() => {
            const el = document.querySelector('.inner');
            el.style.height = 'auto';
            const h = el.scrollHeight;
            el.style.height = '';
            return h;
        }""")
        if h * mid <= container_h:
            lo = mid
        else:
            hi = mid
    return lo


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main render
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render(claims: list[dict], theme: str = "slate") -> list[Path]:
    """Render all claims to 3 independent formats."""
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(exist_ok=True)
    paths = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        for i, claim in enumerate(claims):
            # ── 橫式 (1080×auto) ──
            html = render_html_wide(claim, theme)
            page.set_viewport_size({"width": 1080, "height": 800})
            page.set_content(html, wait_until="networkidle")
            height = page.evaluate("document.querySelector('.card').offsetHeight")
            height = max(height, 400)
            page.set_viewport_size({"width": 1080, "height": height})
            out = OUTPUT_DIR / f"claim_{i+1}.png"
            page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1080, "height": height})
            paths.append(out)

            # ── Reels (1080×1920) ──
            page.set_viewport_size({"width": 1080, "height": 1920})
            scale = _find_best_scale(page, render_html_reels, claim, theme, 1920)
            html = render_html_reels(claim, theme, font_scale=scale)
            page.set_content(html, wait_until="networkidle")
            out = OUTPUT_DIR / f"claim_{i+1}_reels.png"
            page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            paths.append(out)

            # ── Square (1080×1080) ──
            page.set_viewport_size({"width": 1080, "height": 1080})
            scale = _find_best_scale(page, render_html_square, claim, theme, 1080)
            html = render_html_square(claim, theme, font_scale=scale)
            page.set_content(html, wait_until="networkidle")
            out = OUTPUT_DIR / f"claim_{i+1}_square.png"
            page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
            paths.append(out)

        browser.close()
    return paths
