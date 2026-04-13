# Scorecard: Variant — Hybrid Retrieval (RRF)

**Generated:** 2026-04-13 17:43  
**Config:** `variant_hybrid`  
**Test set:** 10 câu hỏi  

---

## Summary

| Metric | Avg Score | Bar |
|--------|-----------|-----|
| Faithfulness | 3.70/5 | ███░░ |
| Relevance | 3.80/5 | ███░░ |
| Context Recall | 5.00/5 | █████ |
| Completeness | 3.50/5 | ███░░ |

**Overall avg:** `4.00/5`

---

## Per-Question Results

| ID | Category | Difficulty | Faithful | Relevant | Recall | Complete | Latency |
|----|----------|------------|----------|----------|--------|----------|---------|
| q01 | SLA | easy | 5 | 5 | 5 | 5 | 3392ms |
| q02 | Refund | easy | 4 | 5 | 5 | 5 | 2738ms |
| q03 | Access Control | medium | 5 | 5 | 5 | 5 | 2612ms |
| q04 | Refund | medium | 5 | 5 | 5 | 4 | 2323ms |
| q05 | IT Helpdesk | easy | 5 | 5 | 5 | 5 | 2437ms |
| q06 | SLA | medium | 5 | 5 | 5 | 5 | 3918ms |
| q07 | Access Control | hard | 1 | 1 | 5 | 1 | 2741ms |
| q08 | HR Policy | easy | 5 | 5 | 5 | 3 | 2099ms |
| q09 | Insufficient Context | hard | 1 | 1 | None | 1 | 2024ms |
| q10 | Refund | hard | 1 | 1 | 5 | 1 | 1875ms |

---

## Câu Hỏi Yếu Nhất

### [q09] ERR-403-AUTH là lỗi gì và cách xử lý?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=None | C=1
- **Notes:** Câu trả lời không có thông tin nào từ ngữ cảnh, hoàn toàn không liên quan.

### [q07] Approval Matrix để cấp quyền hệ thống là tài liệu nào?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=5 | C=1
- **Notes:** Câu trả lời không có bất kỳ thông tin nào liên quan đến ngữ cảnh đã retrieve, hoàn toàn không grounded.

### [q10] Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=5 | C=1
- **Notes:** Câu trả lời 'Không đủ dữ liệu' không bám vào ngữ cảnh đã cung cấp, vì ngữ cảnh đã nêu rõ các điều kiện và quy trình hoàn tiền.

