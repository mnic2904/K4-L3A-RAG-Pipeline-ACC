import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _extract_pdf_fallback(path: Path) -> str:
    """Trích xuất nội dung văn bản từ PDF bằng pdfplumber nếu MarkItDown không lấy được."""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
        return "\n\n".join(texts).strip()
    except Exception:
        return ""


def convert_legal_docs() -> None:
    """Chuyển đổi các tài liệu pháp lý (PDF/DOCX) sang Markdown trong data/standardized/legal/."""
    from markitdown import MarkItDown
    
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not legal_dir.exists():
        return
        
    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            output_file = output_dir / f"{path.stem}.md"
            content = ""
            try:
                result = converter.convert(str(path))
                if result and result.text_content:
                    content = result.text_content.strip()
            except Exception as error:
                print(f"MarkItDown warning on {path.name}: {error}")
                
            # Fallback nếu MarkItDown không trích xuất đủ nội dung
            if len(content) < 100 and path.suffix.lower() == ".pdf":
                fallback_text = _extract_pdf_fallback(path)
                if len(fallback_text) > len(content):
                    content = fallback_text
                    
            if content:
                output_file.write_text(content, encoding="utf-8")
                print(f"Converted legal: {path.name} -> {output_file.name}")
            else:
                print(f"Warning: Không thể trích xuất văn bản từ {path.name}")


def convert_news_articles() -> None:
    """Chuyển đổi các bài viết đã crawl (JSON) sang Markdown trong data/standardized/news/."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not news_dir.exists():
        return
        
    for path in sorted(news_dir.glob("*.json")):
        output_file = output_dir / f"{path.stem}.md"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            content = data.get("content_markdown", "").strip()
            if not content:
                continue
                
            title = data.get("title", path.stem).strip()
            url = data.get("url", "").strip()
            date_crawled = data.get("date_crawled", "").strip()
            
            header = (
                f"# {title}\n\n"
                f"**Source:** {url}\n\n"
                f"**Crawled:** {date_crawled}\n\n---\n\n"
            )
            output_file.write_text(header + content, encoding="utf-8")
            print(f"Converted news: {path.name} -> {output_file.name}")
        except Exception as error:
            print(f"Failed to convert {path.name}: {error}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing (legal + news) sang standardized Markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()

