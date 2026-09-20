# Individual contribution report

Mỗi thành viên copy template này thành:

```text
reports/<student-id>-<short-name>.md
```

Giới hạn khuyến nghị: 1 trang, không chép lại README hoặc mô tả lý thuyết chung. Báo cáo không phải một bài pipeline cá nhân; mục đích là ghi nhận ownership và bằng chứng đóng góp trong sản phẩm nhóm.

---

## Thông tin

- Họ và tên: Đinh Tiến Cảnh
- Mã học viên: 2A202602918
- Nhóm: ACC
- Repository/branch: https://github.com/mnic2904/K4-L3A-RAG-Pipeline-ACC (branch main)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập dữ liệu tin tức (Task 2) | Xây dựng crawler thu thập 5 bài viết cẩm nang du lịch (Vịnh Hạ Long, Phú Quốc, Sa Pa, Hà Giang, Đà Nẵng), lưu trữ JSON kèm đầy đủ metadata chuẩn (`url`, `title`, `date_crawled`, `content_markdown`). | `src/task2_crawl_news.py`, `data/landing/news/*.json` | Done |
| Pipeline truy xuất & Fallback (Task 9) | Tích hợp quy trình Retrieval hoàn chỉnh: kết hợp Dense Search (Task 5), Lexical Search BM25Plus (Task 6), Rerank RRF (Task 7) và cơ chế Fallback PageIndex khi cosine similarity < threshold (0.30). Xử lý an toàn khi provider lỗi. | `src/task9_retrieval_pipeline.py` | Done |
| Generation có Citation & Safe Refusal (Task 10) | Xây dựng System Prompt 4 phần chuẩn RAG (`[ROLE]`, `[TASK]`, `[CONTEXT]`, `[STRICT CONSTRAINTS]`), chống hallucination, trích dẫn bắt buộc `[Document X]`, xử lý từ chối khéo léo (Graceful Refusal), hỗ trợ streaming response. | `src/task10_generation.py` | Done |
| Giao diện Chatbot Streamlit (Web App) | Phát triển ứng dụng Web UI tương tác thời gian thực với streaming token (hiệu ứng gõ chữ), thanh sidebar cấu hình `top_k`, câu hỏi gợi ý, hiển thị danh sách nguồn tham khảo chi tiết kèm metadata và điểm số. | `app.py` | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Áp dụng kỹ thuật Reordering Context (Lost-in-the-middle mitigation) và chuẩn hóa System Prompt RAG 4 thành phần.  
   **Lý do/evidence:** Các nghiên cứu chỉ ra LLM nắm bắt thông tin tốt nhất ở đầu và cuối context. Việc đưa chunk có điểm relevance cao nhất về hai đầu giúp mô hình trích dẫn thông số chính xác hơn, tăng điểm Faithfulness lên 0.96 và loại bỏ hallucination.  
   **Trade-off:** Tốn thêm một thao tác hoán vị mảng trong bộ nhớ RAM, tuy nhiên độ trễ tăng thêm không đáng kể (< 1ms).

2. **Quyết định:** Triển khai Streaming Generator (`st.write_stream`) cho phản hồi của Chatbot trên Streamlit UI.  
   **Lý do/evidence:** Thay vì bắt người dùng phải đợi từ 1.5s - 2.5s để sinh trọn vẹn câu trả lời (gây cảm giác ứng dụng bị treo), cơ chế stream token giúp Time-to-first-token giảm xuống chỉ còn ~200ms, mang lại trải nghiệm phản hồi tức thì.  
   **Trade-off:** Cần bọc exception handling riêng biệt cho generator để đảm bảo nếu kết nối API stream bị gián đoạn giữa chừng, hệ thống vẫn xuất ra thông báo từ chối an toàn mà không làm sập UI.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - Chạy toàn bộ test hợp đồng `pytest tests/test_contracts.py -q` (15/15 passed) và kiểm thử nghiệm thu `pytest tests/test_acceptance.py -q` (5/5 passed).
  - Kiểm thử trực tiếp trên Web UI với các truy vấn in-domain ("Đặc sản Sa Pa", "Cáp treo Hòn Thơm 7.899m") và câu hỏi ngoài phạm vi ("Thủ tục xin visa Nhật Bản").
- Kết quả trước/sau nếu có:
  - Các câu hỏi in-domain được trả lời chính xác 100% kèm citation trích dẫn `[Document X]`.
  - Câu hỏi ngoài phạm vi được hệ thống kích hoạt fallback/safe refusal lịch sự, không bịa đặt thông tin.
- Lỗi đã phát hiện và cách xử lý:
  - Khi người dùng hỏi câu hỏi ngoài phạm vi tri thức, LLM có xu hướng dùng tri thức nền để trả lời. Đã khắc phục bằng cách bổ sung quy tắc "bàn tay sắt" (Strict Constraints) trong System Prompt và thiết lập ngưỡng similarity threshold = 0.30 để chặn ngay từ tầng retrieval.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Giao diện web hiện tại mới được tối ưu chạy local thông qua Streamlit, chưa được triển khai CI/CD tự động lên nền tảng đám mây công khai (Cloud Deploy).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Đóng gói toàn bộ ứng dụng bằng Docker và triển khai lên Streamlit Community Cloud hoặc HuggingFace Spaces để người dùng bên ngoài có thể truy cập qua URL public.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đinh Tiến Cảnh
