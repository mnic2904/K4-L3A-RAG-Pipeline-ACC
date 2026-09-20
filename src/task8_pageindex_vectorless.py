"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pageindex import PageIndexClient


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / "pageindex_doc_ids.json"
PDF_CACHE_DIR = Path(__file__).parent.parent / "pageindex_pdfs"
RETRIEVAL_TIMEOUT_SECONDS = 30.0
POLL_INTERVAL_SECONDS = 0.5


def _get_client() -> PageIndexClient:
    """Tạo PageIndex client và báo lỗi cấu hình rõ ràng."""
    api_key = PAGEINDEX_API_KEY or os.getenv("PAGEINDEX_API_KEY", "")
    if not api_key:
        raise RuntimeError("PAGEINDEX_API_KEY is not configured")
    return PageIndexClient(api_key=api_key)


def _load_document_ids() -> dict[str, str]:
    """Đọc cache source -> doc_id; cache lỗi được xem như cache rỗng."""
    if not CACHE_FILE.exists():
        return {}
    try:
        raw_cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw_cache, dict):
        return {}

    document_ids: dict[str, str] = {}
    for source, value in raw_cache.items():
        # Chấp nhận cả cache cũ dạng {source: {"doc_id": ...}}.
        doc_id = value.get("doc_id") if isinstance(value, dict) else value
        if isinstance(source, str) and isinstance(doc_id, str) and doc_id:
            document_ids[source] = doc_id
    return document_ids


def _save_document_ids(document_ids: dict[str, str]) -> None:
    """Ghi cache nguyên tử để tránh file JSON dở dang khi chương trình bị dừng."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = CACHE_FILE.with_suffix(CACHE_FILE.suffix + ".tmp")
    temporary_file.write_text(
        json.dumps(document_ids, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_file.replace(CACHE_FILE)


def _find_unicode_font() -> Path | None:
    """Tìm font Unicode phổ biến để giữ được tiếng Việt khi tạo PDF."""
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    )
    return next((path for path in candidates if path.exists()), None)


def _markdown_to_pdf(source_path: Path) -> Path:
    """Chuyển Markdown thành PDF văn bản để SDK PageIndex 0.2.8 upload được."""
    from fpdf import FPDF

    relative_path = source_path.relative_to(STANDARDIZED_DIR)
    output_path = (PDF_CACHE_DIR / relative_path).with_suffix(".pdf")
    if (
        output_path.exists()
        and output_path.stat().st_mtime >= source_path.stat().st_mtime
    ):
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = source_path.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    unicode_font = _find_unicode_font()
    if unicode_font is not None:
        pdf.add_font("DocumentFont", fname=str(unicode_font))
        pdf.set_font("DocumentFont", size=10)
    else:
        # Core font chỉ hỗ trợ Latin-1; thay ký tự lạ thay vì làm upload crash.
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        pdf.set_font("Helvetica", size=10)

    for line in text.splitlines() or [""]:
        pdf.multi_cell(
            w=0,
            h=5,
            text=line or " ",
            new_x="LMARGIN",
            new_y="NEXT",
            wrapmode="CHAR",
        )
    pdf.output(str(output_path))
    return output_path


def _source_metadata(source: str) -> dict[str, Any]:
    """Khôi phục metadata contract từ tài liệu chuẩn hóa tương ứng."""
    source_path = STANDARDIZED_DIR / Path(source)
    title = source_path.stem
    url: str | None = None
    doc_type = "legal" if "legal" in Path(source).parts else "news"

    try:
        resolved_source = source_path.resolve()
        if not resolved_source.is_relative_to(STANDARDIZED_DIR.resolve()):
            raise ValueError("source is outside standardized directory")
        text = resolved_source.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
        source_match = re.search(
            r"^\*\*Source:\*\*\s*(\S+)", text, flags=re.MULTILINE
        )
        if title_match:
            title = title_match.group(1).strip()
        if source_match and source_match.group(1).lower() != "unknown":
            url = source_match.group(1).strip()
    except (OSError, UnicodeError, ValueError):
        pass

    return {
        "source": Path(source).name,
        "title": title,
        "doc_type": doc_type,
        "url": url,
    }


def _wait_for_retrieval(
    client: PageIndexClient,
    retrieval_id: str,
) -> dict[str, Any]:
    """Poll retrieval đến khi hoàn thành nhưng không chờ vô hạn."""
    deadline = time.monotonic() + RETRIEVAL_TIMEOUT_SECONDS
    while True:
        response = client.get_retrieval(retrieval_id)
        status = str(response.get("status", "")).lower()
        if status in {"completed", "complete", "success", "succeeded", "ready"}:
            return response
        if status in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError(f"PageIndex retrieval ended with status={status}")
        if response.get("retrieved_nodes") is not None:
            return response
        if time.monotonic() >= deadline:
            raise TimeoutError("PageIndex retrieval timed out")
        time.sleep(POLL_INTERVAL_SECONDS)


def _number(value: object) -> float | None:
    """Đổi một API score hợp lệ thành float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value) if isinstance(value, str) and value.strip() else None
    except ValueError:
        return None


def _parse_retrieval(
    response: dict[str, Any],
    source: str,
    doc_id: str,
    rank_offset: int,
) -> list[dict]:
    """Đổi retrieved_nodes (kể cả relevant_contents lồng nhau) sang contract."""
    payload = response.get("result")
    if isinstance(payload, dict):
        response = payload
    nodes = response.get("retrieved_nodes", response.get("nodes", []))
    if not isinstance(nodes, list):
        return []

    metadata = _source_metadata(source)
    parsed: list[dict] = []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        contents = node.get("relevant_contents")
        if not isinstance(contents, list) or not contents:
            contents = [node]

        for content_index, content_item in enumerate(contents):
            if isinstance(content_item, str):
                content_data: dict[str, Any] = {"relevant_content": content_item}
            elif isinstance(content_item, dict):
                content_data = content_item
            else:
                continue

            content = next(
                (
                    value.strip()
                    for value in (
                        content_data.get("relevant_content"),
                        content_data.get("content"),
                        content_data.get("text"),
                        node.get("relevant_content"),
                        node.get("content"),
                        node.get("text"),
                    )
                    if isinstance(value, str) and value.strip()
                ),
                "",
            )
            if not content:
                continue

            score = next(
                (
                    numeric_score
                    for numeric_score in (
                        _number(content_data.get("relevance_score")),
                        _number(content_data.get("score")),
                        _number(node.get("relevance_score")),
                        _number(node.get("score")),
                    )
                    if numeric_score is not None
                ),
                None,
            )
            fallback_rank = rank_offset + len(parsed) + 1
            if score is None:
                score = 1.0 / fallback_rank

            page_value = content_data.get("page_index", node.get("page_index"))
            try:
                chunk_index = max(0, int(page_value))
            except (TypeError, ValueError):
                chunk_index = node_index

            node_id = node.get("node_id", node.get("id", node_index))
            identity = (
                f"{source}|{doc_id}|{node_id}|{content_index}|{chunk_index}|{content}"
            )
            digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:20]
            parsed.append(
                {
                    "id": f"pageindex::{digest}",
                    "content": content,
                    "score": score,
                    "metadata": {**metadata, "chunk_index": chunk_index},
                    "retrieval_method": "pageindex",
                }
            )
    return parsed


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    # TODO: Upload documents và lưu mapping source -> document ID.
    #
    # Nếu SDK không nhận Markdown, convert sang PDF tạm trước khi upload.
    # Kiểm tra response thật của SDK thay vì đoán tên field.
    client = _get_client()
    document_ids = _load_document_ids()
    supported_suffixes = {".md", ".markdown", ".pdf"}

    for source_path in sorted(STANDARDIZED_DIR.rglob("*")):
        if not source_path.is_file() or source_path.suffix.lower() not in supported_suffixes:
            continue
        source = source_path.relative_to(STANDARDIZED_DIR).as_posix()
        if source in document_ids:
            continue

        upload_path = (
            _markdown_to_pdf(source_path)
            if source_path.suffix.lower() in {".md", ".markdown"}
            else source_path
        )
        response = client.submit_document(str(upload_path))
        doc_id = response.get("doc_id") if isinstance(response, dict) else None
        if not isinstance(doc_id, str) or not doc_id:
            raise RuntimeError(f"PageIndex did not return doc_id for {source}")
        document_ids[source] = doc_id
        # Lưu sau từng file để lần chạy sau không upload lại các file đã thành công.
        _save_document_ids(document_ids)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    # TODO: Query các document IDs và parse retrieved nodes.
    #
    # Mỗi result cần: id, content, score, metadata, retrieval_method.
    # Nếu API không trả score, có thể gán score giảm dần theo rank.
    if top_k <= 0 or not query.strip():
        return []

    document_ids = _load_document_ids()
    if not document_ids:
        return []
    try:
        client = _get_client()
    except RuntimeError:
        return []

    results: list[dict] = []
    seen_ids: set[str] = set()
    for source, doc_id in document_ids.items():
        try:
            submitted = client.submit_query(doc_id, query)
            retrieval_id = (
                submitted.get("retrieval_id") if isinstance(submitted, dict) else None
            )
            if not isinstance(retrieval_id, str) or not retrieval_id:
                continue
            response = _wait_for_retrieval(client, retrieval_id)
            parsed = _parse_retrieval(response, source, doc_id, len(results))
        except Exception:
            # Một document/provider lỗi không được làm hỏng toàn bộ fallback pipeline.
            continue

        for item in parsed:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                results.append(item)

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    upload_documents()
