"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os
import sys
import warnings

from dotenv import load_dotenv

warnings.filterwarnings("ignore")

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import multiprocess.resource_tracker
    multiprocess.resource_tracker.ResourceTracker.__del__ = lambda self: None
except (ImportError, AttributeError):
    pass


from .task9_retrieval_pipeline import retrieve


load_dotenv()


TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """[ROLE]
Bạn là trợ lý AI chuyên nghiệp về thông tin du lịch và chính sách, hỗ trợ người dùng giải đáp các thắc mắc một cách chính xác, khách quan và đáng tin cậy.

[TASK]
Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách mạch lạc, đầy đủ và dễ hiểu dựa trên thông tin được cung cấp trong phần Context.

[CONTEXT]
Context được cung cấp chứa các đoạn trích từ tài liệu hệ thống, được đánh số rõ ràng theo định dạng [Document X | Title: ... | Source: ...].

[STRICT CONSTRAINTS - BÀN TAY SẮT]
1. Grounding & Citation: Mọi khẳng định, dữ liệu, số liệu hoặc mốc thời gian đưa ra BẮT BUỘC phải kèm theo trích dẫn nguồn tương ứng dưới dạng [Document X].
2. Anti-Hallucination: Tuyệt đối CHỈ sử dụng thông tin có trong Context. Không tự suy đoán, không bổ sung kiến thức bên ngoài nếu không có trong tài liệu.
3. Graceful & Helpful Refusal (Nghệ thuật từ chối khéo léo):
   - Khi Context KHÔNG có thông tin hoặc thiếu dữ liệu để trả lời, TUYỆT ĐỐI KHÔNG trả lời cộc lốc như "Tôi không biết" hay chỉ một câu ngắn gây ức chế cho người dùng.
   - Hãy phản hồi theo công thức 3 bước lịch sự và hữu ích:
     + Bước 1 (Thông báo nhã nhặn): "Rất tiếc, trong các tài liệu cẩm nang du lịch và văn bản chính sách hiện có trong hệ thống, tôi chưa tìm thấy thông tin cụ thể về [chủ đề/câu hỏi của bạn]."
     + Bước 2 (Gợi ý phạm vi dữ liệu): Nhắc nhẹ những chủ đề mà hệ thống đang có dữ liệu đầy đủ nhất để hỗ trợ (ví dụ: cẩm nang du lịch Phú Quốc, Sa Pa, Đà Nẵng, Hà Giang, Vịnh Hạ Long, hoặc quy hoạch du lịch).
     + Bước 3 (Định hướng tiếp theo): Gợi ý người dùng thử đặt lại câu hỏi với từ khóa cụ thể hơn hoặc tham khảo các cổng thông tin chính thức."""




def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context để giảm lost-in-the-middle."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label rõ ràng cho LLM tạo citation."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        title = meta.get("title", "Unknown")
        source = meta.get("source", "Unknown")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình trong .env."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").lower().strip()
    model_name = os.getenv("LLM_MODEL") or ""

    if provider == "openai":
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment")
        client = OpenAI(api_key=api_key)
        model = model_name or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return (response.choices[0].message.content or "").strip()

    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment")
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model = model_name or "gemini-2.0-flash"
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                ),
            )
            return (response.text or "").strip()
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=model_name or "gemini-2.0-flash",
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_message,
                generation_config={"temperature": TEMPERATURE, "top_p": TOP_P},
            )
            return (response.text or "").strip()

    elif provider == "anthropic":
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment")
        client = anthropic.Anthropic(api_key=api_key)
        model = model_name or "claude-3-5-sonnet-20241022"
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.content[0].text.strip()

def stream_llm(system_prompt: str, user_message: str):
    """Gọi LLM và stream từng token/từ theo thời gian thực."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").lower().strip()
    model_name = os.getenv("LLM_MODEL") or ""

    if provider == "openai":
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment")
        client = OpenAI(api_key=api_key)
        model = model_name or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment")
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model = model_name or "gemini-2.0-flash"
            response = client.models.generate_content_stream(
                model=model,
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                ),
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=model_name or "gemini-2.0-flash",
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_message,
                stream=True,
                generation_config={"temperature": TEMPERATURE, "top_p": TOP_P},
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

    elif provider == "anthropic":
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment")
        client = anthropic.Anthropic(api_key=api_key)
        model = model_name or "claude-3-5-sonnet-20241022"
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        ) as stream:
            for text in stream.text_stream:
                yield text
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


DEFAULT_REFUSAL_MESSAGE = (
    "Rất tiếc, trong cơ sở dữ liệu cẩm nang du lịch và chính sách hiện tại của hệ thống, "
    "tôi chưa tìm thấy thông tin phù hợp để trả lời câu hỏi của bạn. "
    "Bạn có thể thử đặt lại câu hỏi với từ khóa cụ thể hơn hoặc khám phá các chủ đề có sẵn như: "
    "du lịch Phú Quốc, Sa Pa, Đà Nẵng, Hà Giang, Vịnh Hạ Long hay quy hoạch phát triển du lịch."
)


def generate_stream_with_citation(query: str, top_k: int = TOP_K):
    """Trả về generator sinh câu trả lời từng từ, kèm danh sách sources và retrieval_source."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        def empty_stream():
            yield DEFAULT_REFUSAL_MESSAGE
        return empty_stream(), [], "none"

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"

    def response_generator():
        try:
            for token in stream_llm(SYSTEM_PROMPT, user_message):
                yield token
        except Exception as error:
            print(f"Warning: Streaming error ({error}), returning fallback message.")
            yield DEFAULT_REFUSAL_MESSAGE

    return response_generator(), chunks, retrieval_source


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Sinh câu trả lời kèm citation từ kết quả retrieval (phiên bản đầy đủ)."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": DEFAULT_REFUSAL_MESSAGE,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"Warning: LLM generation error ({error}), returning safe refusal.")
        answer = DEFAULT_REFUSAL_MESSAGE

    method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }




if __name__ == "__main__":
    test_query = "Đặc sản nổi tiếng ở Sa Pa gồm những món gì?"
    print(f"=== Đang xử lý câu hỏi: '{test_query}' ===")
    result = generate_with_citation(test_query)
    print("\n[CÂU TRẢ LỜI]")
    print(result["answer"])
    print(f"\n[PHƯƠNG THỨC TRUY XUẤT]: {result['retrieval_source']}")
    print(f"[SỐ LƯỢNG NGUỒN TRÍCH DẪN]: {len(result['sources'])} chunks")


