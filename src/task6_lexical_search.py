import warnings

warnings.filterwarnings("ignore")

try:
    import multiprocess.resource_tracker
    multiprocess.resource_tracker.ResourceTracker.__del__ = lambda self: None
except (ImportError, AttributeError):
    pass


CORPUS: list[dict] = []



def _get_corpus() -> list[dict]:
    """Lấy corpus chunks, tự động load từ Task 4 nếu CORPUS rỗng."""
    global CORPUS
    if not CORPUS:
        try:
            from .task4_chunking_indexing import chunk_documents, load_documents
            CORPUS = chunk_documents(load_documents())
        except Exception:
            pass
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Plus
    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Plus(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = _get_corpus()
    if not corpus:
        return []
    import numpy as np
    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(query.lower().split())
    # argsort returns indices in ascending order, so we reverse it
    indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for index in indices:
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[index]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for result in lexical_search("du lịch Phú Quốc", top_k=3):
        print(result)

