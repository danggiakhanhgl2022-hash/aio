import time
import pandas as pd

from src.vector_db import retrieve_chunks
from src.rag_pipeline import generate_answer
from src.config import (
    LLM_MODEL,
    EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    N_RESULTS,
    TEMPERATURE
)


def run_evaluation(collection, questions_csv_path="evaluation_questions.csv"):
    """
    Chạy test câu hỏi từ file CSV.
    Lưu ý: phần chấm điểm vẫn để con người chấm thủ công.
    """

    df = pd.read_csv(questions_csv_path)

    results = []

    config_id = (
        f"llm={LLM_MODEL}|embed={EMBED_MODEL}|"
        f"chunk={CHUNK_SIZE}|overlap={CHUNK_OVERLAP}|"
        f"k={N_RESULTS}|temp={TEMPERATURE}"
    )

    for _, row in df.iterrows():
        question = row["question"]
        expected_answer = row.get("expected_answer", "")
        question_type = row.get("type", "")

        start_time = time.time()

        retrieved_chunks = retrieve_chunks(
            collection=collection,
            question=question,
            n_results=N_RESULTS
        )

        answer = generate_answer(question, retrieved_chunks)

        elapsed_time = round(time.time() - start_time, 2)

        results.append({
            "config_id": config_id,
            "question": question,
            "expected_answer": expected_answer,
            "question_type": question_type,
            "answer": answer,
            "retrieved_context": "\n\n---\n\n".join(retrieved_chunks),
            "response_time_seconds": elapsed_time,
            "correctness": "",
            "groundedness": "",
            "completeness": "",
            "clarity": "",
            "refusal": "",
            "total_score": "",
            "notes": ""
        })

    result_df = pd.DataFrame(results)
    result_df.to_csv("evaluation_results.csv", index=False, encoding="utf-8-sig")

    return result_df