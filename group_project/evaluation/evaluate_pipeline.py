"""Script chạy đánh giá thực nghiệm A/B giữa Config A (Dense-only) và Config B (Hybrid + RRF)."""

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Set utf-8 stdout
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import format_context, reorder_for_llm, call_llm, SYSTEM_PROMPT


EVAL_DIR = Path(__file__).parent
GOLDEN_PATH = EVAL_DIR / "golden_dataset.json"


def evaluate_retrieval_metrics(retrieved_chunks: list[dict], expected_context: str) -> dict:
    """Tính toán sơ bộ Context Recall và Context Precision đối chiếu với Ground Truth."""
    if not retrieved_chunks:
        return {"recall": 0.0, "precision": 0.0}

    expected_words = set(expected_context.lower().split())
    if not expected_words:
        return {"recall": 1.0, "precision": 1.0}

    hits = 0
    relevant_chunks = 0
    all_retrieved_words = set()

    for idx, chunk in enumerate(retrieved_chunks):
        content = chunk.get("content", "").lower()
        chunk_words = set(content.split())
        all_retrieved_words.update(chunk_words)

        overlap = len(expected_words.intersection(chunk_words))
        if overlap >= min(5, len(expected_words) // 3):
            hits += (relevant_chunks + 1) / (idx + 1)
            relevant_chunks += 1

    precision = hits / len(retrieved_chunks) if retrieved_chunks else 0.0
    covered_words = len(expected_words.intersection(all_retrieved_words))
    recall = min(1.0, covered_words / max(1, len(expected_words)))

    return {"recall": round(recall, 4), "precision": round(precision, 4)}


def run_single_config(item: dict, use_reranking: bool, top_k: int = 5) -> dict:
    """Chạy câu hỏi qua 1 cấu hình retrieval và sinh câu trả lời."""
    question = item["question"]
    expected_context = item["expected_context"]

    chunks = retrieve(question, top_k=top_k, use_reranking=use_reranking)
    metrics = evaluate_retrieval_metrics(chunks, expected_context)

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as e:
        answer = f"Lỗi sinh câu trả lời: {e}"

    return {
        "question": question,
        "answer": answer,
        "sources_count": len(chunks),
        "recall": metrics["recall"],
        "precision": metrics["precision"],
    }


def run_full_ab_evaluation():
    if not GOLDEN_PATH.exists():
        print(f"Không tìm thấy file: {GOLDEN_PATH}")
        return

    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    print(f"=== Bắt đầu đánh giá A/B trên {len(dataset)} câu hỏi Golden Dataset ===")
    print("-" * 75)

    scores_a = {"recall": [], "precision": []}
    scores_b = {"recall": [], "precision": []}

    for idx, item in enumerate(dataset, 1):
        q = item["question"]
        print(f"\n[{idx}/{len(dataset)}] Câu hỏi: {q}")

        # Config A: Dense Only
        res_a = run_single_config(item, use_reranking=False, top_k=5)
        scores_a["recall"].append(res_a["recall"])
        scores_a["precision"].append(res_a["precision"])
        print(f"  -> Config A (Dense-only): Recall={res_a['recall']:.2f}, Precision={res_a['precision']:.2f}")

        # Config B: Hybrid + RRF
        res_b = run_single_config(item, use_reranking=True, top_k=5)
        scores_b["recall"].append(res_b["recall"])
        scores_b["precision"].append(res_b["precision"])
        print(f"  -> Config B (Hybrid+RRF): Recall={res_b['recall']:.2f}, Precision={res_b['precision']:.2f}")

    avg_recall_a = sum(scores_a["recall"]) / len(scores_a["recall"])
    avg_prec_a = sum(scores_a["precision"]) / len(scores_a["precision"])
    avg_recall_b = sum(scores_b["recall"]) / len(scores_b["recall"])
    avg_prec_b = sum(scores_b["precision"]) / len(scores_b["precision"])

    print("\n" + "=" * 75)
    print("=== TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ A/B ===")
    print(f"Config A (Dense-only)  : Avg Recall = {avg_recall_a:.4f} | Avg Precision = {avg_prec_a:.4f}")
    print(f"Config B (Hybrid + RRF): Avg Recall = {avg_recall_b:.4f} | Avg Precision = {avg_prec_b:.4f}")
    print(f"Delta (B - A)          : Recall = +{avg_recall_b - avg_recall_a:.4f} | Precision = +{avg_prec_b - avg_prec_a:.4f}")
    print("=" * 75)


if __name__ == "__main__":
    run_full_ab_evaluation()
