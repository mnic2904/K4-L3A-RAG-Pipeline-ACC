"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

-> Dùng Jina hoặc self host hoặc bất cứ công cụ nào bạn quen
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    # TODO: Implement RRF.
    #
    # scores = {}
    # items = {}
    # for ranked_list in ranked_lists:
    #     for rank, item in enumerate(ranked_list, 1):
    #         item_id = item["id"]
    #         scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
    #         items[item_id] = item
    #
    # ranked_ids = sorted(scores, key=scores.get, reverse=True)
    # results = []
    # for item_id in ranked_ids[:top_k]:
    #     result = items[item_id].copy()
    #     result["score"] = scores[item_id]
    #     result["retrieval_method"] = "hybrid"
    #     results.append(result)
    # return results
    if top_k <= 0:
        return []
    if k < 0:
        raise ValueError("k must be non-negative")

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        # Một tài liệu chỉ được đóng góp một lần trong mỗi bảng xếp hạng.
        seen_ids: set[str] = set()
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item["id"]
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            # Giữ dữ liệu của lần xuất hiện đầu tiên và chỉ thay score/method ở output.
            items.setdefault(item_id, item)

    # Python sort ổn định, nên các tài liệu đồng điểm giữ thứ tự xuất hiện đầu tiên.
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


if __name__ == "__main__":
    print("Implement rerank_rrf, then run contract tests.")
