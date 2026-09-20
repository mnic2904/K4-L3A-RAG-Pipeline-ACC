"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://vnexpress.net/cam-nang-du-lich-vinh-ha-long-4626380.html",
    "https://vnexpress.net/cam-nang-du-lich-phu-quoc-4106697.html",
    "https://mia.vn/cam-nang-du-lich/dac-san-sapa-net-dac-trung-trong-nen-am-thuc-xu-so-suong-mu-657",
    "https://vnexpress.net/cam-nang-du-lich-ha-giang-4445788.html",
    "https://vnexpress.net/cam-nang-du-lich-da-nang-4470111.html"
]


async def crawl_article(url: str) -> dict:
    from datetime import datetime
    import asyncio
    
    def fetch():
        from markitdown import MarkItDown
        md = MarkItDown()
        return md.convert(url)
        
    result = await asyncio.to_thread(fetch)
    
    # Extract a simple title from the URL if not available
    title = result.title if hasattr(result, "title") and result.title else url.strip("/").split("/")[-1].title()
    
    return {
        "url": url,
        "title": title or "Unknown",
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": result.text_content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
