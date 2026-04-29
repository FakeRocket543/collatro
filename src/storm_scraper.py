"""風傳媒評論爬蟲 - channel 3/48/49，2023-01-01 至今"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.storm.mg"
CHANNELS = [3, 48, 49]
START_DATE = datetime(2023, 1, 1)
DELAY_LIST = 1.5
DELAY_ARTICLE = 2.5
OUTPUT_DIR = Path("/Users/fl/Python/tea_goose/anseropolis/data/storm")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def fetch(url: str) -> str | None:
    for attempt in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        wait = 10 * (attempt + 1)
        print(f"    ⏳ retry {attempt+1}, wait {wait}s")
        time.sleep(wait)
    return None


def parse_list_page(html: str) -> list[dict]:
    """從列表頁解析文章 ID 與日期，透過日期文字節點往上找文章連結。"""
    soup = BeautifulSoup(html, "html.parser")
    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}")
    results = []
    seen = set()

    for d_el in soup.find_all(string=date_pattern):
        date_text = d_el.strip()
        # 只取合法日期格式
        m = re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", date_text)
        if not m:
            continue
        # 往上找包含 article link 的容器
        node = d_el.parent
        for _ in range(8):
            node = node.parent
            if not node:
                break
            link = node.find("a", href=re.compile(r"^/article/\d+"))
            if link:
                aid = re.search(r"/article/(\d+)", link["href"]).group(1)
                if aid not in seen:
                    seen.add(aid)
                    results.append({"id": aid, "url": f"{BASE}/article/{aid}", "date": m.group(0)})
                break

    return results


def parse_article(html: str) -> dict:
    """從文章頁解析標題、作者、日期、正文。"""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # 作者 - 找帶有紅色樣式的 author link（文章作者區塊）
    author = ""
    for link in soup.find_all("a", href=re.compile(r"^/author/\d+"), class_=re.compile(r"text-smg-red")):
        t = link.get_text(strip=True)
        if t:
            author = t
            break

    # 日期 - 從 meta 或文字
    pub_date = ""
    meta_date = soup.find("meta", {"property": "article:published_time"})
    if meta_date:
        pub_date = meta_date.get("content", "")
    if not pub_date:
        text = soup.get_text()
        m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", text)
        if m:
            pub_date = m.group(1)

    # 正文
    body = ""
    for selector in ["article", ".article_content", ".article-content"]:
        el = soup.select_one(selector)
        if el:
            for tag in el.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            paragraphs = el.find_all("p")
            if paragraphs:
                body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                break
    if not body:
        all_p = soup.find_all("p")
        body = "\n\n".join(p.get_text(strip=True) for p in all_p if len(p.get_text(strip=True)) > 20)

    # 關鍵字
    keywords = []
    for kw_link in soup.find_all("a", href=re.compile(r"^/keyword/")):
        kw = kw_link.get_text(strip=True)
        if kw and kw not in keywords:
            keywords.append(kw)

    return {"title": title, "author": author, "date": pub_date, "body": body, "keywords": keywords}


def scrape_channel(channel_id: int):
    """爬取單一頻道所有文章直到 START_DATE。"""
    output_dir = OUTPUT_DIR / f"channel_{channel_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    progress_file = output_dir / "_progress.json"
    if progress_file.exists():
        progress = json.loads(progress_file.read_text())
    else:
        progress = {"last_page": 0, "scraped_ids": []}

    scraped_ids = set(progress["scraped_ids"])
    page = progress["last_page"] + 1
    stop = False

    print(f"\n{'='*60}")
    print(f"Channel {channel_id} - 從第 {page} 頁開始")
    print(f"已爬取 {len(scraped_ids)} 篇")
    print(f"{'='*60}")

    while not stop:
        url = f"{BASE}/channel/all/{channel_id}/{page}"
        print(f"\n[列表] 第 {page} 頁: {url}")

        html = fetch(url)
        if not html:
            print("  ⚠ 無法取得頁面，結束")
            break

        articles = parse_list_page(html)
        if not articles:
            print("  ⚠ 無文章，結束")
            break

        new_count = 0
        for art in articles:
            # 檢查列表頁日期
            try:
                art_date = datetime.strptime(art["date"], "%Y-%m-%d %H:%M")
                if art_date < START_DATE:
                    print(f"  ⏹ 到達起始日期 ({art['date']})，停止")
                    stop = True
                    break
            except ValueError:
                pass

            if art["id"] in scraped_ids:
                continue

            print(f"  📄 {art['id']}", end=" ")
            article_html = fetch(art["url"])
            if not article_html:
                print("❌")
                continue

            data = parse_article(article_html)
            data["id"] = art["id"]
            data["url"] = art["url"]
            data["channel"] = channel_id

            # 再次用文章頁日期確認
            if data["date"]:
                try:
                    d = data["date"][:16]
                    check_date = datetime.strptime(d, "%Y-%m-%d %H:%M")
                    if check_date < START_DATE:
                        print(f"⏹ {d}")
                        stop = True
                        break
                except ValueError:
                    pass

            out_file = output_dir / f"{art['id']}.json"
            out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            scraped_ids.add(art["id"])
            new_count += 1
            print(f"✅ {data.get('title', '')[:30]}")
            time.sleep(DELAY_ARTICLE)

        print(f"  → 本頁新增 {new_count} 篇")

        # 儲存進度
        progress["last_page"] = page
        progress["scraped_ids"] = list(scraped_ids)
        progress_file.write_text(json.dumps(progress, ensure_ascii=False))

        page += 1
        time.sleep(DELAY_LIST)

    print(f"\nChannel {channel_id} 完成，共 {len(scraped_ids)} 篇")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {OUTPUT_DIR}")
    print(f"目標日期: {START_DATE.strftime('%Y-%m-%d')} 至今")
    print(f"頻道: {CHANNELS}")

    for ch in CHANNELS:
        scrape_channel(ch)

    print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
