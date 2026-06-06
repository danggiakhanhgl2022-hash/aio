from typing import List, Tuple
from .loader import TextChunk
from .utils import norm


def score_chunk(question: str, chunk: TextChunk) -> float:
    q = norm(question)
    t = norm(chunk.text)

    if not q or not t:
        return 0.0

    q_terms = [x for x in q.split() if len(x) >= 2]
    if not q_terms:
        return 0.0

    score = 0.0

    # phrase bonus
    if q in t:
        score += 8.0

    # token overlap
    t_set = set(t.split())
    for term in q_terms:
        if term in t_set:
            score += 1.5
        elif term in t:
            score += 0.5

    # title/heading strong
    if t.startswith(q[:40]):
        score += 3.0

    return score


def retrieve_chunks(question: str, chunks: List[TextChunk], top_k: int = 5) -> List[Tuple[float, TextChunk]]:
    scored = []
    for ch in chunks:
        s = score_chunk(question, ch)
        if s > 0:
            scored.append((s, ch))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]
