"""爬取中時電子報五類言論全文（2023-01-01 至今）
策略：從 sitemap 收集所有 opinion URL → 過濾分類 → 逐篇抓全文

用法:
    python3 -u -m src.scrape_chinatimes
"""

import json
import time
import re
from datetime import datetime
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

print = partial(print, flush=True)

# 分類代碼對應（從 URL 尾碼判斷）
CAT_CODES = {
    "262101": "中時社論",
    "262102": "旺報社評",
    "262113": "工商社論",
    "262103": "快評",
    "262104": "時論廣場",
}

START_DATE = "20230101"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "chinatimes"
DELAY_SITEMAP = 3.0
DELAY_ARTICLE = 1.5


def collect_opinion_urls(page) -> dict[str, list[str]]:
    """從 sitemap index 收集所有 opinion URLs，按分類分組。"""
    print("=== 第一階段：從 sitemap 收集文章 URL ===")

    # 先抓 sitemap index
    page.goto(
        "https://www.chinatimes.com/sitemaps/sitemap_article_all_index_0.xml",
        wait_until="domcontentloaded", timeout=30000,
    )
    time.sleep(3)
    content = page.content()

    sitemap_urls = re.findall(
        r"https://www\.chinatimes\.com/sitemaps/article_sitemaps/sitemap_article_\d+\.xml",
        content,
    )
    print(f"  找到 {len(sitemap_urls)} 個子 sitemap")

    # 按分類收集
    urls_by_cat: dict[str, set[str]] = {cat: set() for cat in CAT_CODES.values()}
    progress_file = OUTPUT_DIR / "_sitemap_progress.json"

    if progress_file.exists():
        progress = json.loads(progress_file.read_text())
        done_sitemaps = set(progress.get("done", []))
        for cat, url_list in progress.get("urls", {}).items():
            if cat in urls_by_cat:
                urls_by_cat[cat] = set(url_list)
        print(f"  恢復進度：已處理 {len(done_sitemaps)} 個 sitemap")
    else:
        done_sitemaps = set()

    for i, sm_url in enumerate(sitemap_urls):
        if sm_url in done_sitemaps:
            continue

        page.goto(sm_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        sm_content = page.content()

        # 找日期範圍
        dates = re.findall(r"/opinion/(\d{8})\d+-\d+", sm_content)
        if dates and max(dates) < START_DATE:
            print(f"  [{i+1}/{len(sitemap_urls)}] {sm_url.split('/')[-1]} → 日期 {max(dates)} < 2023，跳過後續")
            break
        if dates and min(dates) < START_DATE:
            # 部分在範圍內
            pass

        # 收集 opinion URLs（去重，去 ?chdtv 後綴）
        opinion_matches = re.findall(
            r"https://www\.chinatimes\.com/opinion/(\d{8})(\d+)-(\d+)",
            sm_content,
        )
        new_count = 0
        for date_str, art_num, cat_code in opinion_matches:
            if date_str < START_DATE:
                continue
            if cat_code not in CAT_CODES:
                continue
            cat_name = CAT_CODES[cat_code]
            url = f"https://www.chinatimes.com/opinion/{date_str}{art_num}-{cat_code}"
            if url not in urls_by_cat[cat_name]:
                urls_by_cat[cat_name].add(url)
                new_count += 1

        done_sitemaps.add(sm_url)

        if new_count > 0 or (i + 1) % 10 == 0:
            total = sum(len(v) for v in urls_by_cat.values())
            print(f"  [{i+1}/{len(sitemap_urls)}] {sm_url.split('/')[-1]} +{new_count} (累計 {total})")

        # 每 10 個存一次進度
        if (i + 1) % 10 == 0:
            progress_file.write_text(json.dumps({
                "done": list(done_sitemaps),
                "urls": {k: list(v) for k, v in urls_by_cat.items()},
            }, ensure_ascii=False))

        time.sleep(DELAY_SITEMAP)

    # 最終存進度
    progress_file.write_text(json.dumps({
        "done": list(done_sitemaps),
        "urls": {k: list(v) for k, v in urls_by_cat.items()},
    }, ensure_ascii=False))

    print("\n  === URL 收集完成 ===")
    for cat, urls in urls_by_cat.items():
        print(f"  {cat}: {len(urls)} 篇")

    return {k: sorted(v) for k, v in urls_by_cat.items()}


def fetch_article(page, url: str) -> dict | None:
    """抓取單篇文章全文。"""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("div.article-body", timeout=8000)
    except Exception:
        return None

    title = ""
    h1 = page.query_selector("h1.article-title, h1")
    if h1:
        title = h1.inner_text().strip()

    # 日期
    pub_date = ""
    header = page.query_selector("header.article-header, .article-meta, .post-time")
    if header:
        txt = header.inner_text()
        m = re.search(r"(\d{4}/\d{2}/\d{2})", txt)
        if m:
            pub_date = m.group(1)
    if not pub_date:
        m = re.search(r"(\d{4}/\d{2}/\d{2})", page.inner_text("body")[:2000])
        if m:
            pub_date = m.group(1)

    # 正文
    body = ""
    el = page.query_selector("div.article-body")
    if el:
        body = el.inner_text().strip()

    if not body or len(body) < 50:
        return None

    return {"title": title, "date": pub_date, "url": url, "body": body}


def scrape_articles(page, urls_by_cat: dict[str, list[str]]):
    """第二階段：逐篇抓取全文。"""
    print("\n=== 第二階段：抓取文章全文 ===")

    for cat_name, urls in urls_by_cat.items():
        cat_dir = OUTPUT_DIR / cat_name
        cat_dir.mkdir(parents=True, exist_ok=True)

        # 載入已完成的
        done_file = cat_dir / "_done.json"
        done_urls = set()
        if done_file.exists():
            done_urls = set(json.loads(done_file.read_text()))

        remaining = [u for u in urls if u not in done_urls]
        print(f"\n[{cat_name}] 共 {len(urls)} 篇，已完成 {len(done_urls)}，剩餘 {len(remaining)}")

        for i, url in enumerate(remaining):
            data = fetch_article(page, url)
            if data:
                data["category"] = cat_name
                art_id = url.rstrip("/").split("/")[-1]
                out_file = cat_dir / f"{art_id}.json"
                out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                done_urls.add(url)

                if (i + 1) % 20 == 0:
                    print(f"  [{cat_name}] {i+1}/{len(remaining)} ✅")
            else:
                done_urls.add(url)  # 標記為已處理（避免重試失敗的）

            # 每 50 篇存一次
            if (i + 1) % 50 == 0:
                done_file.write_text(json.dumps(list(done_urls), ensure_ascii=False))

            time.sleep(DELAY_ARTICLE)

        done_file.write_text(json.dumps(list(done_urls), ensure_ascii=False))
        actual = len(list(cat_dir.glob("*.json"))) - 1  # 扣掉 _done.json
        print(f"  [{cat_name}] 完成，實際存檔 {actual} 篇")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {OUTPUT_DIR}")
    print(f"目標: 2023-01-01 至今")
    print(f"分類: {list(CAT_CODES.values())}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        urls_by_cat = collect_opinion_urls(page)
        scrape_articles(page, urls_by_cat)

        browser.close()

    print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
