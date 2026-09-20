# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Custom Evaluation Pipeline (ChromaDB 0.4.24, Rank-BM25 0.2.2) |
| Evaluator model                    | LLM-as-a-Judge (OpenAI GPT-4o-mini) & Word Overlap Heuristic |
| Generator model                    | OpenAI gpt-4o-mini |
| Embedding model                    | BAAI/bge-m3 |
| Corpus version/commit              | Main branch (3 legal PDFs, 5 standardized travel markdown articles) |
| Golden dataset size                | 18 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | Cosine score threshold = 0.30 calibrated trên 18 test cases |

## Configurations

- **Config A — dense-only:** ChromaDB semantic search với embedding model BAAI/bge-m3, cosine similarity, lấy top_k=5 chunks (use_reranking=False).
- **Config B — hybrid + RRF:** Dense search (ChromaDB) kết hợp Sparse search (BM25Plus), gộp thứ hạng bằng Reciprocal Rank Fusion (k=60), lấy top_k=5 chunks (use_reranking=True).

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |     0.88 |     0.96 |     +0.08 |
| Answer relevance  |     0.85 |     0.94 |     +0.09 |
| Context recall    |     0.65 |     0.75 |     +0.10 |
| Context precision |     0.58 |     0.69 |     +0.11 |
| **Average**       |     0.74 |    0.835 |    +0.095 |

## A/B comparison

- Cấu hình tốt hơn: Config B (Hybrid + RRF) tốt hơn Config A với Context Recall tăng +0.10 và Context Precision tăng +0.11.
- Evidence: Khi chạy thực nghiệm trên 18 câu hỏi đa dạng (trực tiếp, dài dòng, thừa ngữ cảnh nhiễu, thiếu ngữ cảnh cộc lốc, sai chính tả, ngoài phạm vi), Config B đạt Avg Recall 0.7488 và Avg Precision 0.6913, vượt trội so với Config A (Avg Recall 0.6461, Avg Precision 0.5798). Đặc biệt ở các câu hỏi chứa thực thể địa danh hoặc từ khóa cộc lốc, BM25 giúp kéo các chunk liên quan trực tiếp lên đầu.
- Trade-off về latency/cost: Config B tăng độ trễ thêm ~15-25ms do tính toán BM25 và RRF trong RAM (hoàn toàn không đáng kể so với thời gian LLM sinh câu trả lời ~800ms - 1.2s), chi phí API LLM giữ nguyên do cả 2 config đều gửi top_k=5 chunks.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Tôi dự định mua áo khoác gió The North Face và máy ảnh Sony A7IV để đi phượt cung Tây Bắc - Đông Bắc, đoạn qua đèo Mã Pí Lèng ở Hà Giang thì con đèo này nối hai huyện nào và từ đỉnh đèo ngắm được dòng sông với hẻm vực nào? | Config A |         0.75 |      0.80 |   0.55 |      0.50 | retrieval                 | Câu hỏi chứa nhiều thông tin ngoại cảnh gây nhiễu khiến vector embedding bị lệch, bỏ sót chunk chứa thông tin địa lý đèo Mã Pí Lèng nối Đồng Văn - Mèo Vạc. |
|   2 | hang động danh thắng vịnh hạ long | Config A |         0.80 |      0.82 |   0.60 |      0.55 | retrieval                 | Câu hỏi dạng từ khóa ngắn thiếu ngữ cảnh khiến Dense search match vào các đoạn văn bản giới thiệu chung thay vì chunk danh sách các hang động Sửng Sốt, Thiên Cung, Đầu Gỗ. |
|   3 | an goi ca trich o phu kuoc thi an kem voi cai j va cham nuoc mam j z? | Config B |         0.88 |      0.90 |   0.70 |      0.65 | retrieval                 | Câu hỏi sai chính tả và viết tắt làm giảm khả năng match từ khóa chính xác của BM25, dù semantic search vẫn vớt lại được chunk ẩm thực liên quan. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Duy trì Hybrid Search (Dense + BM25 + RRF) làm mặc định | Config B tăng Recall từ 0.65 lên 0.75 và Precision từ 0.58 lên 0.69 trên 18 câu hỏi thực nghiệm | Đảm bảo khả năng truy xuất chính xác cho cả câu hỏi ngữ nghĩa và câu hỏi chứa từ khóa thực thể | Chạy lại script evaluate_pipeline.py và đối chiếu điểm số |
|        2 | Bổ sung module chuẩn hóa câu hỏi và sửa lỗi chính tả trước retrieval | Câu hỏi có từ sai chính tả và viết tắt làm giảm điểm số BM25 | Tăng hiệu quả của nhánh lexical search khi người dùng gõ sai hoặc gõ tắt | Kiểm thử độ chính xác trên nhóm câu hỏi có lỗi chính tả |
|        3 | Áp dụng kỹ thuật Reordering Context (Lost-in-the-middle) | Đặt các chunk điểm cao ở đầu và cuối context giúp LLM sinh câu trả lời bám sát tài liệu hơn | Nâng cao điểm Faithfulness và giảm thiểu hallucination | So sánh điểm Faithfulness trước và sau khi bật reorder_for_llm |

## Bonus experiments
| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| TODO       | TODO     |         TODO |               TODO | TODO       |
