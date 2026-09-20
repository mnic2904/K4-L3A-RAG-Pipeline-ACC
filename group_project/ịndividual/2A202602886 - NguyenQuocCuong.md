# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Nguyễn Quốc Cường
- Mã học viên: 2A202602886
- Nhóm: ACC
- Repository/branch: https://github.com/mnic2904/K4-L3A-RAG-Pipeline-ACC (`main`)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — Thu thập tài liệu legal | Cài đặt chức năng tạo thư mục và tải 3 PDF công khai về chiến lược, quy hoạch du lịch Phú Thọ, Phú Quốc và Việt Nam; đặt tên file ổn định để phục vụ chuẩn hóa và indexing. | `src/task1_collect_legal_docs.py`; `data/landing/legal/`; commits `5c00e37`, `1524df8` | Done |
| Task 7 — Reciprocal Rank Fusion | Cài đặt RRF theo thứ hạng để gộp dense và BM25 bằng ID; loại ID trùng trong từng danh sách, giữ thứ tự ổn định khi đồng điểm, giới hạn `top_k` và trả `retrieval_method="hybrid"`. | `src/task7_reranking.py`; commit `38d11fc` | Done |
| Task 8 — PageIndex fallback | Tích hợp PageIndex: quản lý API key, chuyển Markdown sang PDF có hỗ trợ tiếng Việt, cache `doc_id`, polling có timeout, parse kết quả về `SearchResult` và cô lập lỗi provider để pipeline không bị crash. | `src/task8_pageindex_vectorless.py`; commit `38d11fc` | Done |
| Golden dataset | Xây dựng 18 case từ corpus legal và news, gồm câu trực tiếp, dài dòng có nhiễu, từ khóa ngắn, sai chính tả và câu ngoài phạm vi; mỗi case có `question`, `expected_answer`, `expected_context`. | `group_project/evaluation/golden_dataset.json`; commit `4c5c089` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng RRF theo thứ hạng thay vì cộng trực tiếp cosine score và BM25 score.
   **Lý do/evidence:** Hai retriever có thang điểm khác nhau. Trên cùng 18 golden cases và `top_k=5`, Hybrid + RRF đạt điểm trung bình `0.835`, cao hơn dense-only `0.74`; context recall tăng từ `0.65` lên `0.75` và context precision tăng từ `0.58` lên `0.69`.
   **Trade-off:** Tăng khoảng 15–25 ms do chạy thêm BM25 và RRF trong RAM, nhưng không tăng chi phí LLM vì hai cấu hình đều gửi 5 chunks.

2. **Quyết định:** Thiết kế golden set có nhiều kiểu diễn đạt và case gây nhiễu, đồng thời giữ PageIndex là fallback chịu lỗi.
   **Lý do/evidence:** `RESULT.md` cho thấy dense search dễ lệch với câu dài có thông tin ngoại cảnh, còn BM25 giảm hiệu quả khi câu sai chính tả. Hai câu ngoài phạm vi kiểm tra khả năng fallback/safe refusal thay vì buộc hệ thống trả lời.
   **Trade-off:** Bộ 18 câu phản ánh nhiều lỗi thực tế hơn nhưng kích thước còn nhỏ; PageIndex phụ thuộc API ngoài và chưa được tách thành một cấu hình đánh giá riêng trong báo cáo nhóm.

## Kiểm thử và kết quả

- Đã kiểm tra contract của RRF: gộp đúng thứ hạng, loại trùng và đánh dấu kết quả `hybrid`; acceptance test xác nhận đủ tài liệu legal và golden dataset hợp lệ.
- Theo `group_project/evaluation/RESULT.md`, Config B tăng Faithfulness `+0.08`, Answer relevance `+0.09`, Context recall `+0.10` và Context precision `+0.11` so với Config A.
- Case kém nhất của dense-only là câu hỏi Mã Pí Lèng có nhiều chi tiết nhiễu (`recall=0.55`, `precision=0.50`). Case sai chính tả về gỏi cá trích vẫn là điểm yếu của hybrid (`recall=0.70`, `precision=0.65`).
- Lỗi/rủi ro đã nhận diện: truy vấn ngắn dễ lấy đoạn giới thiệu chung; câu sai chính tả làm giảm match BM25; cần dùng cosine score gốc thay vì RRF score khi quyết định fallback.

## Điều còn hạn chế

- Kết quả mới dựa trên 18 case và evaluator kết hợp GPT-4o-mini với word-overlap heuristic, nên chưa đại diện đầy đủ cho mọi cách hỏi và có thể chịu sai số của LLM-as-a-Judge.
- Nếu có thêm thời gian, tôi sẽ bổ sung bước chuẩn hóa/sửa chính tả trước retrieval, mở rộng golden set theo từng nhóm lỗi và đo riêng PageIndex về chất lượng, latency và chi phí.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Quốc Cường
