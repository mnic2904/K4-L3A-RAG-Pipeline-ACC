"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    # TODO: Có thể tải thủ công hoặc dùng requests.
    #
    # Ví dụ:
    import requests
    
    sources = {
        "nghien-cuu-chien-luoc-phat-trien-du-lich-phu-tho.pdf": "https://tapchi.tueba.edu.vn/wp-content/uploads/2026/07/Nguyen-Thi-Thuy.pdf",
        "phu-luc-bao-cao-quy-hoach-he-thong-du-lich-viet-nam.pdf": "https://images.vietnamtourism.gov.vn/vn//dmdocuments/2022/220925_Phu_luc_BCTT_QHHT_DL.pdf",
        "nghien-cuu-chien-luoc-phat-trien-du-lich-tp-phu-quoc.pdf": "https://tapchi.tueba.edu.vn/wp-content/uploads/2021/04/Nguyen-Danh-Nam.pdf"
    }
    for filename, url in sources.items():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        (DATA_DIR / filename).write_bytes(response.content)
    # raise NotImplementedError("Implement download_documents")


if __name__ == "__main__":
    setup_directory()
    download_documents()
