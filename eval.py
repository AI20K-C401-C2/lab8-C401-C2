"""
eval.py — Sprint 4: Evaluation & Scorecard
==========================================
Mục tiêu Sprint 4 (60 phút):
  - Chạy 10 test questions qua pipeline
  - Chấm điểm theo 4 metrics: Faithfulness, Relevance, Context Recall, Completeness
  - So sánh baseline vs variant
  - Ghi kết quả ra scorecard & grading log

Owner: Ngọc (Evaluation + Docs Owner)
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from rag_answer import rag_answer

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"
LOGS_DIR = Path(__file__).parent / "logs"

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

BASELINE_CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "baseline_dense",
}

VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "variant_hybrid",
}


# =============================================================================
# LLM-as-Judge helper
# =============================================================================

def _call_judge(prompt: str) -> Dict[str, Any]:
    """
    Gọi LLM làm judge, trả về dict {"score": int, "reason": str}.
    Fallback về {"score": None, "reason": "error"} nếu parse thất bại.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        import re
        json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        # Thử extract số điểm cuối cùng từ text
        nums = re.findall(r"\b([1-5])\b", raw)
        if nums:
            return {"score": int(nums[0]), "reason": raw[:200]}
        return {"score": None, "reason": raw[:200]}
    except Exception as e:
        return {"score": None, "reason": str(e)}


# =============================================================================
# SCORING FUNCTIONS — LLM-as-Judge
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Faithfulness: Câu trả lời có bám đúng chứng cứ đã retrieve không?
    Thang điểm 1-5 (5 = hoàn toàn grounded).
    """
    if not chunks_used:
        return {"score": 1, "notes": "Không có chunk nào được retrieve — không thể verify grounding"}

    context = "\n\n".join([c.get("text", "") for c in chunks_used[:3]])
    prompt = f"""Bạn là chuyên gia đánh giá hệ thống RAG (Retrieval-Augmented Generation).

Ngữ cảnh đã retrieve:
---
{context[:2000]}
---

Câu trả lời của hệ thống:
---
{answer}
---

Đánh giá "Faithfulness" (câu trả lời có bám vào ngữ cảnh không) theo thang 1-5:
5 = Mọi thông tin đều có trong context (hoàn toàn grounded)
4 = Gần như hoàn toàn grounded, tối đa 1 chi tiết nhỏ chưa chắc
3 = Phần lớn grounded, một số thông tin có thể từ model knowledge
2 = Nhiều thông tin không có trong context
1 = Câu trả lời không grounded, phần lớn là bịa

Chỉ trả về JSON: {{"score": <1-5>, "reason": "<lý do ngắn>"}}"""

    result = _call_judge(prompt)
    return {"score": result.get("score"), "notes": result.get("reason", "")}


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer Relevance: Answer có trả lời đúng câu hỏi không?
    Thang điểm 1-5 (5 = trả lời trực tiếp và đầy đủ).
    """
    prompt = f"""Bạn là chuyên gia đánh giá hệ thống RAG.

Câu hỏi: {query}

Câu trả lời của hệ thống: {answer}

Đánh giá "Answer Relevance" (câu trả lời có đúng trọng tâm không) theo thang 1-5:
5 = Trả lời trực tiếp và đầy đủ câu hỏi
4 = Trả lời đúng nhưng thiếu vài chi tiết phụ
3 = Có liên quan nhưng chưa đúng trọng tâm
2 = Lạc đề một phần
1 = Không trả lời câu hỏi

Chỉ trả về JSON: {{"score": <1-5>, "reason": "<lý do ngắn>"}}"""

    result = _call_judge(prompt)
    return {"score": result.get("score"), "notes": result.get("reason", "")}


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    """
    Context Recall: Retriever có mang về đủ evidence cần thiết không?
    Tính theo partial match với tên file (0.0 - 1.0), convert sang 0-5.
    """
    if not expected_sources:
        return {"score": None, "recall": None, "notes": "No expected sources (abstain case)"}

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    found = 0
    missing = []
    for expected in expected_sources:
        # Partial match trên tên file (bỏ extension, bỏ thư mục)
        expected_stem = Path(expected).stem.replace("-", "_").lower()
        matched = any(expected_stem in r.lower().replace("-", "_") for r in retrieved_sources)
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources)
    score = round(recall * 5)  # 0.0→0, 0.5→2-3, 1.0→5

    return {
        "score": score,
        "recall": recall,
        "found": found,
        "total_expected": len(expected_sources),
        "missing": missing,
        "notes": f"Hit {found}/{len(expected_sources)} expected sources" +
                 (f". Missing: {missing}" if missing else ""),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    """
    Completeness: Answer có đầy đủ thông tin so với expected không?
    Thang điểm 1-5 (5 = bao gồm đủ tất cả điểm quan trọng).
    """
    if not expected_answer:
        return {"score": None, "notes": "Không có expected_answer để so sánh"}

    prompt = f"""Bạn là chuyên gia đánh giá hệ thống RAG.

Câu hỏi: {query}

Câu trả lời kỳ vọng:
{expected_answer}

Câu trả lời của hệ thống:
{answer}

Đánh giá "Completeness" (độ đầy đủ so với expected) theo thang 1-5:
5 = Bao gồm đủ tất cả điểm quan trọng trong expected
4 = Thiếu 1 chi tiết nhỏ
3 = Thiếu một số thông tin quan trọng
2 = Thiếu nhiều thông tin quan trọng
1 = Thiếu phần lớn nội dung cốt lõi

Chỉ trả về JSON: {{"score": <1-5>, "reason": "<lý do ngắn>"}}"""

    result = _call_judge(prompt)
    return {"score": result.get("score"), "notes": result.get("reason", "")}


# =============================================================================
# SCORECARD RUNNER
# =============================================================================

def run_scorecard(
    config: Dict[str, Any],
    test_questions: Optional[List[Dict]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Chạy toàn bộ test questions qua pipeline và chấm điểm.
    Trả về list rows — mỗi row là một câu hỏi với đầy đủ scores.
    """
    if test_questions is None:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

    results = []
    label = config.get("label", "unnamed")

    print(f"\n{'='*70}")
    print(f"Chạy scorecard: {label}")
    print(f"Config: retrieval_mode={config.get('retrieval_mode')} | "
          f"top_k={config.get('top_k_search')}->{config.get('top_k_select')} | "
          f"rerank={config.get('use_rerank')}")
    print('='*70)

    for q in test_questions:
        question_id = q["id"]
        query = q["question"]
        expected_answer = q.get("expected_answer", "")
        expected_sources = q.get("expected_sources", [])
        category = q.get("category", "")
        difficulty = q.get("difficulty", "")

        if verbose:
            print(f"\n[{question_id}] ({category}/{difficulty}) {query}")

        # --- Gọi pipeline ---
        run_start = datetime.now()
        try:
            result = rag_answer(
                query=query,
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
                use_rerank=config.get("use_rerank", False),
                verbose=False,
            )
            answer = result["answer"]
            chunks_used = result["chunks_used"]
            error = None
        except Exception as e:
            answer = f"PIPELINE_ERROR: {e}"
            chunks_used = []
            error = str(e)

        latency_ms = int((datetime.now() - run_start).total_seconds() * 1000)

        # --- Chấm điểm ---
        faith = score_faithfulness(answer, chunks_used)
        relevance = score_answer_relevance(query, answer)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(query, answer, expected_answer)

        row = {
            "id": question_id,
            "category": category,
            "difficulty": difficulty,
            "query": query,
            "answer": answer,
            "expected_answer": expected_answer,
            "faithfulness": faith["score"],
            "faithfulness_notes": faith.get("notes", ""),
            "relevance": relevance["score"],
            "relevance_notes": relevance.get("notes", ""),
            "context_recall": recall["score"],
            "context_recall_notes": recall.get("notes", ""),
            "completeness": complete["score"],
            "completeness_notes": complete.get("notes", ""),
            "config_label": label,
            "latency_ms": latency_ms,
            "error": error,
        }
        results.append(row)

        if verbose:
            print(f"  → Answer: {answer[:120]}...")
            print(f"  → F:{faith['score']} | R:{relevance['score']} | "
                  f"Rc:{recall['score']} | C:{complete['score']} | {latency_ms}ms")

    # Tính averages
    print(f"\n{'─'*40}")
    print(f"Tóm tắt: {label}")
    for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
        scores = [r[metric] for r in results if r[metric] is not None]
        avg = sum(scores) / len(scores) if scores else None
        bar = "█" * int(avg or 0) + "░" * (5 - int(avg or 0))
        print(f"  {metric:<20} {bar}  {f'{avg:.2f}/5' if avg else 'N/A'}")

    return results


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
) -> None:
    """So sánh baseline vs variant theo từng câu hỏi và tổng thể."""
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<22} {'Baseline':>10} {'Variant':>10} {'Delta':>8}  {'Winner'}")
    print("─" * 62)

    for metric in metrics:
        b_scores = [r[metric] for r in baseline_results if r[metric] is not None]
        v_scores = [r[metric] for r in variant_results if r[metric] is not None]

        b_avg = sum(b_scores) / len(b_scores) if b_scores else None
        v_avg = sum(v_scores) / len(v_scores) if v_scores else None
        delta = (v_avg - b_avg) if (b_avg is not None and v_avg is not None) else None

        b_str = f"{b_avg:.2f}" if b_avg is not None else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg is not None else "N/A"
        d_str = f"{delta:+.2f}" if delta is not None else "N/A"
        winner = ("🟢 Variant" if delta and delta > 0.1
                  else "🔴 Baseline" if delta and delta < -0.1
                  else "⚪ Tie") if delta is not None else "N/A"

        print(f"  {metric:<20} {b_str:>10} {v_str:>10} {d_str:>8}  {winner}")

    print(f"\n{'ID':<6} {'Cat':<16} {'B:F/R/Rc/C':<16} {'V:F/R/Rc/C':<16} {'Better'}")
    print("─" * 65)

    b_by_id = {r["id"]: r for r in baseline_results}
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})

        b_str = "/".join([str(b_row.get(m, "?")) for m in metrics])
        v_str = "/".join([str(v_row.get(m, "?")) for m in metrics])

        b_total = sum(b_row.get(m, 0) or 0 for m in metrics)
        v_total = sum(v_row.get(m, 0) or 0 for m in metrics)
        better = "Variant" if v_total > b_total else ("Baseline" if b_total > v_total else "Tie")

        print(f"  {qid:<4} {v_row.get('category',''):<16} {b_str:<16} {v_str:<16} {better}")

    if output_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / output_csv
        combined = baseline_results + variant_results
        if combined:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"\n✓ CSV lưu tại: {csv_path}")


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_scorecard_summary(results: List[Dict], label: str) -> str:
    """Tạo báo cáo tóm tắt scorecard dạng markdown."""
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    averages = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    config_label = results[0].get("config_label", label) if results else label

    # Tìm câu yếu nhất
    def total_score(r):
        return sum(r.get(m, 0) or 0 for m in metrics)

    sorted_by_score = sorted(results, key=total_score)
    weakest = sorted_by_score[:3] if len(sorted_by_score) >= 3 else sorted_by_score

    md = f"""# Scorecard: {label}

**Generated:** {timestamp}  
**Config:** `{config_label}`  
**Test set:** {len(results)} câu hỏi  

---

## Summary

| Metric | Avg Score | Bar |
|--------|-----------|-----|
"""
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg is not None else "N/A"
        bar = "█" * int(avg or 0) + "░" * (5 - int(avg or 0)) if avg else "─────"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} | {bar} |\n"

    md += "\n**Overall avg:** "
    valid_avgs = [v for v in averages.values() if v is not None]
    overall = sum(valid_avgs) / len(valid_avgs) if valid_avgs else None
    md += f"`{overall:.2f}/5`\n\n" if overall else "N/A\n\n"

    md += "---\n\n## Per-Question Results\n\n"
    md += "| ID | Category | Difficulty | Faithful | Relevant | Recall | Complete | Latency |\n"
    md += "|----|----------|------------|----------|----------|--------|----------|---------|\n"

    for r in results:
        md += (f"| {r['id']} | {r['category']} | {r.get('difficulty','')} "
               f"| {r.get('faithfulness', 'N/A')} "
               f"| {r.get('relevance', 'N/A')} "
               f"| {r.get('context_recall', 'N/A')} "
               f"| {r.get('completeness', 'N/A')} "
               f"| {r.get('latency_ms', '?')}ms |\n")

    md += "\n---\n\n## Câu Hỏi Yếu Nhất\n\n"
    for r in weakest:
        md += f"### [{r['id']}] {r['query']}\n"
        md += f"- **Answer:** {r['answer'][:200]}...\n" if len(r.get('answer','')) > 200 else f"- **Answer:** {r.get('answer','')}\n"
        md += f"- **Scores:** F={r.get('faithfulness','?')} | R={r.get('relevance','?')} | Rc={r.get('context_recall','?')} | C={r.get('completeness','?')}\n"
        md += f"- **Notes:** {r.get('faithfulness_notes','')}\n\n"

    return md


# =============================================================================
# GRADING LOG
# =============================================================================

def save_grading_log(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    run_metadata: Dict[str, Any],
) -> Path:
    """
    Lưu toàn bộ kết quả evaluation ra logs/grading_run.json.
    Format phù hợp với requirements nộp bài.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "grading_run.json"

    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    def calc_avg(results, metric):
        scores = [r[metric] for r in results if r[metric] is not None]
        return round(sum(scores) / len(scores), 2) if scores else None

    log = {
        "run_metadata": {
            **run_metadata,
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(baseline_results),
        },
        "configs": {
            "baseline": BASELINE_CONFIG,
            "variant": VARIANT_CONFIG,
        },
        "summary": {
            "baseline": {m: calc_avg(baseline_results, m) for m in metrics},
            "variant": {m: calc_avg(variant_results, m) for m in metrics},
            "delta": {
                m: (
                    round(calc_avg(variant_results, m) - calc_avg(baseline_results, m), 2)
                    if calc_avg(baseline_results, m) is not None and calc_avg(variant_results, m) is not None
                    else None
                )
                for m in metrics
            },
        },
        "baseline_results": baseline_results,
        "variant_results": variant_results,
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Grading log lưu tại: {log_path}")
    return log_path


# =============================================================================
# MAIN — Chạy evaluation đầy đủ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Sprint 4: Evaluation & Scorecard  [Owner: Ngọc]")
    print("=" * 70)

    # --- Load test questions ---
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)
        print(f"✓ Tìm thấy {len(test_questions)} câu hỏi")
        for q in test_questions:
            print(f"  [{q['id']}] ({q['category']}) {q['question']}")
    except FileNotFoundError:
        print("✗ Không tìm thấy file test_questions.json!")
        exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    run_start_time = datetime.now()

    # --- Chạy Baseline ---
    print("\n" + "─" * 70)
    print("BASELINE: Dense Retrieval")
    print("─" * 70)
    baseline_results = run_scorecard(
        config=BASELINE_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )
    baseline_md = generate_scorecard_summary(baseline_results, "Baseline — Dense Retrieval")
    scorecard_baseline_path = RESULTS_DIR / "scorecard_baseline.md"
    scorecard_baseline_path.write_text(baseline_md, encoding="utf-8")
    print(f"\n✓ Scorecard lưu tại: {scorecard_baseline_path}")

    # --- Chạy Variant (Hybrid) ---
    print("\n" + "─" * 70)
    print("VARIANT: Hybrid Retrieval (Dense + BM25 RRF)")
    print("─" * 70)
    variant_results = run_scorecard(
        config=VARIANT_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )
    variant_md = generate_scorecard_summary(variant_results, "Variant — Hybrid Retrieval (RRF)")
    scorecard_variant_path = RESULTS_DIR / "scorecard_variant.md"
    scorecard_variant_path.write_text(variant_md, encoding="utf-8")
    print(f"\n✓ Scorecard lưu tại: {scorecard_variant_path}")

    # --- A/B Comparison ---
    compare_ab(
        baseline_results,
        variant_results,
        output_csv="ab_comparison.csv",
    )

    # --- Save grading log ---
    total_time_s = int((datetime.now() - run_start_time).total_seconds())
    save_grading_log(
        baseline_results=baseline_results,
        variant_results=variant_results,
        run_metadata={
            "lab": "Day 08 — Full RAG Pipeline",
            "eval_owner": "Ngọc",
            "llm_judge_model": LLM_MODEL,
            "total_run_time_seconds": total_time_s,
            "python_files": ["index.py", "rag_answer.py", "eval.py"],
        },
    )

    print("\n" + "=" * 70)
    print("✓ Sprint 4 hoàn chỉnh! Đầu ra:")
    print(f"  - {scorecard_baseline_path}")
    print(f"  - {scorecard_variant_path}")
    print(f"  - {RESULTS_DIR / 'ab_comparison.csv'}")
    print(f"  - {LOGS_DIR / 'grading_run.json'}")
    print("=" * 70)
