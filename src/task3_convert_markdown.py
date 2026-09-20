"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    from markitdown import MarkItDown
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not legal_dir.exists():
        return
        
    converter = MarkItDown()
    for path in legal_dir.iterdir():
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            output_file = output_dir / f"{path.stem}.md"
            if output_file.exists():
                continue
                
            result = converter.convert(str(path))
            content = result.text_content
            if content and content.strip():
                output_file.write_text(content, encoding="utf-8")
                print(f"Converted: {path.name}")


def convert_news_articles() -> None:
    import json
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not news_dir.exists():
        return
        
    for path in news_dir.glob("*.json"):
        output_file = output_dir / f"{path.stem}.md"
        if output_file.exists():
            continue
            
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            content = data.get("content_markdown", "").strip()
            if not content:
                continue
                
            header = (
                f"# {data.get('title', 'Unknown')}\n\n"
                f"**Source:** {data.get('url', 'Unknown')}\n\n"
                f"**Crawled:** {data.get('date_crawled', 'Unknown')}\n\n---\n\n"
            )
            output_file.write_text(
                header + content, encoding="utf-8"
            )
            print(f"Converted: {path.name}")
        except Exception as e:
            print(f"Failed to convert {path.name}: {e}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
