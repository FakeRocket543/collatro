"""爬取人民日報觀點12個專欄全文（2023-01-01 至今）

策略:
  1. 先從觀點頻道分頁索引抓（最新200條，約到2024年中）
  2. 再從人民日報電子版第05版（評論版）逐日抓取2023年的文章

專欄: 社論、本報評論員、任仲平、任平、仲音、今日談、
      人民論壇、人民觀點、評論員觀察、人民時評、現場評論、望海樓

用法:
    python3 -m src.scrape_people_opinion              # 全部（索引+電子版）
    python3 -m src.scrape_people_opinion --column 社論  # 單一專欄（僅索引）
    python3 -m src.scrape_people_opinion --paper       # 僅電子版歸檔
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 13 個目標專欄 (id, base_url)
_DEFAULT_BASE = "http://opinion.people.com.cn/BIG5/8213/49160"
_ALT_BASE = "http://opinion.people.com.cn/BIG5"

COLUMNS = {
    "社論": ("49179", _DEFAULT_BASE),
    "本報評論員": ("49217", _DEFAULT_BASE),
    "任仲平": ("49205", _DEFAULT_BASE),
    "任平": ("457595", _DEFAULT_BASE),
    "仲音": ("457596", _DEFAULT_BASE),
    "今日談": ("49221", _DEFAULT_BASE),
    "人民論壇": ("49220", _DEFAULT_BASE),
    "人民觀點": ("385787", _DEFAULT_BASE),
    "評論員觀察": ("457597", _DEFAULT_BASE),
    "人民時評": ("49219", _DEFAULT_BASE),
    "現場評論": ("457598", _DEFAULT_BASE),
    "望海樓": ("54773", _DEFAULT_BASE),
    "人民銳評": ("436867", _ALT_BASE),
}

# 用於從標題識別專欄的關鍵字（簡體）
COLUMN_KEYWORDS = [
    "社论", "本报评论员", "任仲平", "任平", "仲音", "今日谈",
    "人民论坛", "人民观点", "评论员观察", "人民时评", "现场评论", "望海楼",
    "人民锐评",
]

PAPER_BASE = "http://paper.people.com.cn/rmrb/html"
START_DATE = datetime(2023, 1, 1)
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "people_opinion"
DELAY_LIST = 1.5
DELAY_ARTICLE = 2.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def fetch(url: str) -> str | None:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    return None


# ─── 方式一：觀點頻道索引 ───────────────────────────────────────

def parse_list_page(html: str) -> list[dict]:
    """解析觀點頻道列表頁。"""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.find_all("li"):
        link = li.find("a", href=re.compile(r"/BIG5/n1/\d{4}/"))
        if not link:
            continue
        title = link.get_text(strip=True)
        href = link.get("href", "")
        li_text = li.get_text()
        m = re.search(r"(\d{4}-\d{2}-\d{2})", li_text)
        date_str = m.group(1) if m else ""
        full_url = f"http://opinion.people.com.cn{href}" if href.startswith("/") else href
        if title and full_url:
            results.append({"title": title, "url": full_url, "date": date_str})
    return results


def parse_article(html: str) -> dict:
    """解析觀點頻道文章頁。"""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    subtitle = ""
    h2 = soup.find("h2")
    if h2:
        subtitle = h2.get_text(strip=True)

    pub_date = ""
    source = ""
    page_text = soup.get_text()
    m = re.search(r"(\d{4})年(\d{2})月(\d{2})日", page_text)
    if m:
        pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m_src = re.search(r"來源：(.+?)[\s\n]", page_text)
    if m_src:
        source = m_src.group(1).strip()

    body = ""
    for sel in [".rm_txt_con", "#rwb_zw", "article", ".text_con", ".box_con"]:
        el = soup.select_one(sel)
        if el:
            for tag in el.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            paragraphs = el.find_all("p")
            if paragraphs:
                body = "\n\n".join(
                    p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
                )
                break
    if not body:
        all_p = soup.find_all("p")
        body = "\n\n".join(
            p.get_text(strip=True) for p in all_p if len(p.get_text(strip=True)) > 50
        )

    return {"title": title, "subtitle": subtitle, "date": pub_date, "source": source, "body": body}


def load_progress(name: str) -> dict:
    f = OUTPUT_DIR / f"{name}_progress.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"last_page": 0, "scraped_urls": []}


def save_progress(name: str, progress: dict):
    f = OUTPUT_DIR / f"{name}_progress.json"
    f.write_text(json.dumps(progress, ensure_ascii=False))


def scrape_column(column: str, col_id: str, base_url: str = _DEFAULT_BASE):
    """從觀點頻道索引爬取單一專欄（最新200條）。"""
    col_dir = OUTPUT_DIR / column
    col_dir.mkdir(parents=True, exist_ok=True)

    progress = load_progress(column)
    scraped_urls = set(progress["scraped_urls"])
    start_page = progress["last_page"] + 1

    print(f"\n{'='*60}")
    print(f"[{column}] 索引模式，從第 {start_page} 頁，已有 {len(scraped_urls)} 篇")
    print(f"{'='*60}")

    page_num = start_page
    consecutive_empty = 0

    while True:
        url = f"{base_url}/{col_id}/index.html" if page_num == 1 else f"{base_url}/{col_id}/index{page_num}.html"
        print(f"\n  📋 第 {page_num} 頁: {url}")
        html = fetch(url)
        if not html:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            page_num += 1
            time.sleep(DELAY_LIST)
            continue

        articles = parse_list_page(html)
        if not articles:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            page_num += 1
            time.sleep(DELAY_LIST)
            continue

        consecutive_empty = 0
        stop = False
        new_count = 0

        for art in articles:
            if art["date"]:
                try:
                    if datetime.strptime(art["date"], "%Y-%m-%d") < START_DATE:
                        stop = True
                        break
                except ValueError:
                    pass

            if art["url"] in scraped_urls:
                continue

            print(f"    📄 {art['title'][:40]}", end=" ")
            article_html = fetch(art["url"])
            if not article_html:
                print("❌")
                continue

            data = parse_article(article_html)
            data["url"] = art["url"]
            data["column"] = column
            if not data["date"] and art["date"]:
                data["date"] = art["date"]

            if data["date"]:
                try:
                    if datetime.strptime(data["date"][:10], "%Y-%m-%d") < START_DATE:
                        stop = True
                        break
                except ValueError:
                    pass

            m_id = re.search(r"c\d+-(\d+)", art["url"])
            slug = m_id.group(1) if m_id else art["url"].rstrip("/").split("/")[-1].replace(".html", "")
            out_file = col_dir / f"{slug}.json"
            out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

            scraped_urls.add(art["url"])
            new_count += 1
            print("✅")
            time.sleep(DELAY_ARTICLE)

        print(f"  → 本頁新增 {new_count} 篇（累計 {len(scraped_urls)}）")
        progress["last_page"] = page_num
        progress["scraped_urls"] = list(scraped_urls)
        save_progress(column, progress)

        if stop:
            break
        page_num += 1
        time.sleep(DELAY_LIST)

    print(f"\n[{column}] 索引完成，共 {len(scraped_urls)} 篇")
    return len(scraped_urls)


# ─── 方式二：電子版歸檔逐日爬取 ─────────────────────────────────

def identify_column(title: str) -> str | None:
    """從標題括號中識別專欄名稱，回傳標準化的專欄名。"""
    for kw in COLUMN_KEYWORDS:
        if kw in title:
            return kw
    return None


def parse_paper_index(html: str, date_str: str) -> list[dict]:
    """解析電子版版面索引頁，回傳該版所有文章連結。"""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.find_all("li"):
        link = li.find("a", href=re.compile(r"nw\.D110000renmrb"))
        if not link:
            continue
        title = link.get_text(strip=True)
        if not title or title.startswith("本版责编") or title == "图片报道":
            continue
        href = link.get("href", "")
        full_url = f"{PAPER_BASE}/{date_str}/{href}"
        results.append({"title": title, "url": full_url, "date": date_str.replace("-", "")})
    return results


def parse_paper_article(html: str) -> str:
    """解析電子版文章頁，提取正文。"""
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")
    body_parts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if not text:
            continue
        if "版权声明" in text or "人民网股份" in text or "人民网版权" in text:
            break
        # 跳過報頭 metadata
        if re.match(r"^人民日报\s*\d{4}年", text):
            continue
        if re.match(r"^\d{4}年\d{2}月\d{2}日\s*星期", text):
            continue
        if len(text) > 20:
            body_parts.append(text)
    return "\n\n".join(body_parts)


def scrape_paper(end_date: str | None = None):
    """從電子版第05版逐日爬取評論文章。"""
    paper_dir = OUTPUT_DIR / "_paper"
    paper_dir.mkdir(parents=True, exist_ok=True)

    # 載入進度
    progress_file = OUTPUT_DIR / "_paper_progress.json"
    if progress_file.exists():
        progress = json.loads(progress_file.read_text())
        last_date = progress.get("last_date", "")
        scraped_urls = set(progress.get("scraped_urls", []))
    else:
        last_date = ""
        scraped_urls = set()

    # 決定起始日期
    if last_date:
        current = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
    else:
        current = START_DATE

    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()

    print(f"\n{'='*60}")
    print(f"[電子版] 從 {current.strftime('%Y-%m-%d')} 到 {end.strftime('%Y-%m-%d')}")
    print(f"已有 {len(scraped_urls)} 篇")
    print(f"{'='*60}")

    total_new = 0

    while current <= end:
        date_str = current.strftime("%Y-%m/%d")  # e.g. "2023-06/15"
        date_ymd = current.strftime("%Y-%m-%d")

        # 第05版（評論版）
        index_url = f"{PAPER_BASE}/{date_str}/nbs.D110000renmrb_05.htm"
        html = fetch(index_url)

        if html:
            articles = parse_paper_index(html, date_str)
            day_new = 0

            for art in articles:
                if art["url"] in scraped_urls:
                    continue

                col = identify_column(art["title"])
                if not col:
                    # 不屬於目標專欄，跳過
                    continue

                # 抓全文
                art_html = fetch(art["url"])
                if not art_html:
                    continue

                body = parse_paper_article(art_html)
                if not body:
                    continue

                data = {
                    "title": art["title"],
                    "column": col,
                    "date": date_ymd,
                    "url": art["url"],
                    "source": "人民日報電子版",
                    "body": body,
                }

                # 存到對應專欄目錄
                col_dir = paper_dir / col
                col_dir.mkdir(parents=True, exist_ok=True)
                slug = re.sub(r"[^\w]", "_", art["title"])[:60]
                out_file = col_dir / f"{date_ymd}_{slug}.json"
                out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

                scraped_urls.add(art["url"])
                day_new += 1
                total_new += 1
                time.sleep(0.5)

            if day_new > 0:
                print(f"  {date_ymd}: +{day_new} 篇")

        # 儲存進度
        progress = {"last_date": date_ymd, "scraped_urls": list(scraped_urls)}
        progress_file.write_text(json.dumps(progress, ensure_ascii=False))

        current += timedelta(days=1)
        time.sleep(0.3)

    print(f"\n[電子版] 完成，新增 {total_new} 篇（累計 {len(scraped_urls)}）")
    return total_new


# ─── 主程式 ─────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="爬取人民日報觀點專欄")
    parser.add_argument("--column", type=str, help="指定單一專欄（僅索引模式）")
    parser.add_argument("--paper", action="store_true", help="僅電子版歸檔模式")
    parser.add_argument("--no-paper", action="store_true", help="跳過電子版歸檔")
    parser.add_argument("--end-date", type=str, help="電子版結束日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {OUTPUT_DIR}")
    print(f"目標: {START_DATE.strftime('%Y-%m-%d')} 至今")

    if args.paper:
        # 僅電子版
        scrape_paper(args.end_date)
        return

    if args.column:
        if args.column not in COLUMNS:
            print(f"❌ 未知專欄: {args.column}")
            print(f"可用: {list(COLUMNS.keys())}")
            return
        columns = {args.column: COLUMNS[args.column]}
    else:
        columns = COLUMNS

    # 步驟一：索引模式
    print(f"\n▶ 步驟一：觀點頻道索引（最新200條）")
    print(f"專欄: {list(columns.keys())}")
    totals = {}
    for col_name, (col_id, base_url) in columns.items():
        totals[col_name] = scrape_column(col_name, col_id, base_url)

    # 步驟二：電子版歸檔（補充2023年文章）
    if not args.no_paper and not args.column:
        print(f"\n▶ 步驟二：電子版歸檔（補充早期文章）")
        scrape_paper(args.end_date)

    print(f"\n{'='*60}")
    print("✅ 全部完成！")
    for col, count in totals.items():
        print(f"  {col}: {count} 篇（索引）")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
