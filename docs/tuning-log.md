# Tuning Log — RAG Pipeline (Day 08 Lab)

> A/B Rule: Chỉ đổi MỘT biến mỗi lần.
> Kết quả được ghi lại từ lần chạy eval.py thực tế ngày 2026-04-13.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode  = "dense"
chunk_strategy  = "parent-child"   # split theo heading === ... ===, child là paragraph
chunk_size      = 400 tokens (~1600 ký tự)   # giới hạn child chunk
top_k_search    = 10
top_k_select    = 3
use_rerank      = False
llm_model       = gpt-4o-mini
```

**Scorecard Baseline:**

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.80 / 5 |
| Answer Relevance | 3.80 / 5 |
| Context Recall | 5.00 / 5 |
| Completeness | 3.20 / 5 |

**Overall avg:** 3.95 / 5

**Kết quả chi tiết từng câu:**

| ID | Category | Difficulty | F | R | Rc | C |
|----|----------|-----------|---|---|----|---|
| q01 | SLA | easy | 5 | 5 | 5 | 5 |
| q02 | Refund | easy | 5 | 5 | 5 | 5 |
| q03 | Access Control | medium | 5 | 5 | 5 | 5 |
| q04 | Refund | medium | 5 | 5 | 5 | 4 |
| q05 | IT Helpdesk | easy | 5 | 5 | 5 | 5 |
| q06 | SLA | medium | 5 | 5 | 5 | **2** |
| q07 | Access Control | hard | **1** | **1** | 5 | **1** |
| q08 | HR Policy | easy | 5 | 5 | 5 | **3** |
| q09 | Insufficient Context | hard | **1** | **1** | N/A | **1** |
| q10 | Refund | hard | **1** | **1** | 5 | **1** |

**Câu hỏi yếu nhất (điểm thấp):**

> - **q07** (Approval Matrix / Access Control — hard): F=1, R=1, Rc=5, C=1. Pipeline retrieve đúng context (Rc=5) nhưng model lại trả lời "Không đủ dữ liệu" dù tài liệu có thông tin. Nguyên nhân: query dùng alias cũ "Approval Matrix" — dense embed không nối được sang tên mới "Access Control SOP", khiến grounded prompt không đủ để model nhận ra.
> - **q09** (ERR-403-AUTH — hard): F=1, R=1, C=1. Đây là câu **không có** đáp án trong docs — pipeline abstain đúng cách ("Không đủ dữ liệu"). Điểm thấp là kỳ vọng, không phải lỗi.
> - **q10** (Hoàn tiền VIP — hard): F=1, R=1, C=1. Docs không đề cập quy trình riêng cho VIP → pipeline abstain đúng. Điểm thấp là kỳ vọng.
> - **q06** (Escalation P1): Completeness=2 — pipeline trả lời đúng về on-call nhưng bỏ sót quy trình escalation 10-phút cụ thể trong expected answer.

**Giả thuyết nguyên nhân (Error Tree):**

- [x] Retrieval: Dense bỏ lỡ exact keyword / alias → **q07** (Approval Matrix ≠ Access Control SOP)
- [x] Generation: Model abstain quá sớm dù context có đủ thông tin → **q07**
- [ ] Indexing: Chunking cắt giữa điều khoản → chưa xác nhận
- [ ] Retrieval: Top-k quá ít → thiếu evidence

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode` từ `"dense"` → `"hybrid"` (Dense 60% + BM25 40%, RRF k=60)  
**Lý do chọn biến này:**

> Baseline analysis cho thấy **q07 (alias query)** là điểm yếu rõ ràng nhất: dense embed không nối được "Approval Matrix" sang "Access Control SOP". Corpus của bài toán chứa **cả hai loại ngôn ngữ:**
> - Ngôn ngữ tự nhiên (policy mô tả quy trình) → Dense mạnh
> - Tên riêng / alias / tên cũ / mã lỗi ("Approval Matrix", "ERR-403-AUTH", "ticket P1") → BM25 mạnh
>
> Thêm BM25 với RRF là cách thay đổi **đúng 1 biến** theo A/B Rule, có lý thuyết hỗ trợ rõ ràng.

**Config thay đổi:**
```
retrieval_mode = "hybrid"    # ← thay đổi duy nhất
dense_weight   = 0.6
sparse_weight  = 0.4
rrf_k          = 60
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**

| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.80/5 | 3.70/5 | -0.10 |
| Answer Relevance | 3.80/5 | 3.80/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.20/5 | **3.60/5** | **+0.40** ✅ |

**Kết quả chi tiết từng câu (Baseline → Variant):**

| ID | Category | B: F/R/Rc/C | V: F/R/Rc/C | Better |
|----|----------|------------|------------|--------|
| q01 | SLA | 5/5/5/5 | 5/5/5/5 | Tie |
| q02 | Refund | 5/5/5/5 | 4/5/5/5 | Baseline |
| q03 | Access Control | 5/5/5/5 | 5/5/5/5 | Tie |
| q04 | Refund | 5/5/5/4 | 5/5/5/4 | Tie |
| q05 | IT Helpdesk | 5/5/5/5 | 5/5/5/5 | Tie |
| q06 | SLA | 5/5/5/**2** | 5/5/5/**5** | **Variant** ✅ |
| q07 | Access Control | 1/1/5/1 | 1/1/5/1 | Tie |
| q08 | HR Policy | 5/5/5/**3** | 5/5/5/**4** | **Variant** ✅ |
| q09 | Insufficient Context | 1/1/N/A/1 | 1/1/N/A/1 | Tie |
| q10 | Refund | 1/1/5/1 | 1/1/5/1 | Tie |

**Nhận xét:**

> **Variant cải thiện rõ ở:**
> - **q06 (Escalation P1)**: Completeness tăng từ 2→5. Hybrid BM25 bắt được từ khóa kỹ thuật "escalate", "10 phút" giúp context đầy đủ hơn về quy trình escalation cụ thể.
> - **q08 (Remote work)**: Completeness tăng từ 3→4. BM25 bắt chính xác từ khóa "probation period" và "2 ngày/tuần".
>
> **Variant kém hơn ở:**
> - **q02 (Refund 7 ngày)**: Faithfulness giảm từ 5→4. Hybrid mang vào thêm chunk từ nhiều nguồn khác nhau, khiến 1 chi tiết nhỏ trong câu trả lời không có trong context gốc.
>
> **Không cải thiện ở q07**: Cả hai đều fail. Vấn đề ở q07 thuộc về **generation layer** (model abstain dù context đủ), không phải retrieval — hybrid không fix được lỗi này.

**Kết luận:**

> Variant 1 (Hybrid) **tốt hơn baseline** nhờ Completeness tăng +0.40. Bằng chứng rõ nhất: q06 (Escalation) tăng từ 2→5, q08 (Remote) tăng từ 3→4.
> Faithfulness giảm nhẹ 0.10 (chấp nhận được — nằm trong biên độ noise của LLM judge).
> **Kết luận: chọn Hybrid làm variant chính thức.**

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > **Generation-layer abstain sai**: Model nói "Không đủ dữ liệu" dù retriever đã lấy đúng context (q07: Rc=5 nhưng F=1). Nguyên nhân: prompt grounding quá nghiêm — khi model không match alias thì chọn abstain thay vì diễn giải. Cần thêm hướng dẫn "nếu tài liệu đề cập chủ đề liên quan, hãy suy luận" hoặc dùng query expansion.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > **`retrieval_mode` (dense vs hybrid)** ảnh hưởng lớn nhất tới Completeness (+0.40). Context Recall đã cao ngay từ baseline (5.00/5) nên không còn nhiều room để improve bằng retrieval tuning. Bước tác động tiếp theo lớn nhất sẽ là **query transformation** (expansion/decomposition) cho alias queries.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > - **Query expansion cho q07**: Dùng LLM sinh 2-3 cách diễn đạt khác của query ("Approval Matrix" → "Access Control SOP", "permission approval document") trước khi retrieve.
   > - **Rerank cross-encoder**: Dense+BM25 retrieve top-10, cross-encoder chấm lại → chọn top-3 sát nhất. Kỳ vọng sẽ fix q06 và q10.
   > - **Prompt engineering**: Thêm hướng dẫn "nếu context có tài liệu về chủ đề liên quan, hãy nêu tên tài liệu đó dù không có đáp án trực tiếp" — fix q07 không tốn chi phí mô hình.
