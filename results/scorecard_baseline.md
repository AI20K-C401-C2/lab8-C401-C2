# Scorecard: Baseline — Dense Retrieval

**Generated:** 2026-04-13 17:42  
**Config:** `baseline_dense`  
**Test set:** 10 câu hỏi  

---

## Summary

| Metric | Avg Score | Bar |
|--------|-----------|-----|
| Faithfulness | 3.70/5 | ███░░ |
| Relevance | 3.80/5 | ███░░ |
| Context Recall | 5.00/5 | █████ |
| Completeness | 3.20/5 | ███░░ |

**Overall avg:** `3.92/5`

---

## Per-Question Results

| ID | Category | Difficulty | Faithful | Relevant | Recall | Complete | Latency |
|----|----------|------------|----------|----------|--------|----------|---------|
| q01 | SLA | easy | 5 | 5 | 5 | 5 | 8546ms |
| q02 | Refund | easy | 4 | 5 | 5 | 5 | 2392ms |
| q03 | Access Control | medium | 5 | 5 | 5 | 5 | 2725ms |
| q04 | Refund | medium | 5 | 5 | 5 | 4 | 2336ms |
| q05 | IT Helpdesk | easy | 5 | 5 | 5 | 5 | 2475ms |
| q06 | SLA | medium | 5 | 5 | 5 | 2 | 4169ms |
| q07 | Access Control | hard | 1 | 1 | 5 | 1 | 2434ms |
| q08 | HR Policy | easy | 5 | 5 | 5 | 3 | 2485ms |
| q09 | Insufficient Context | hard | 1 | 1 | None | 1 | 2435ms |
| q10 | Refund | hard | 1 | 1 | 5 | 1 | 1908ms |

---

## Câu Hỏi Yếu Nhất

### [q09] ERR-403-AUTH là lỗi gì và cách xử lý?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=None | C=1
- **Notes:** Câu trả lời không bám vào ngữ cảnh, không có thông tin nào liên quan đến yêu cầu truy cập.

### [q07] Approval Matrix để cấp quyền hệ thống là tài liệu nào?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=5 | C=1
- **Notes:** Câu trả lời 'Không đủ dữ liệu' không bám vào ngữ cảnh đã retrieve, vì ngữ cảnh đã cung cấp thông tin chi tiết về quy trình cấp phép truy cập.

### [q10] Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?
- **Answer:** Không đủ dữ liệu.
- **Scores:** F=1 | R=1 | Rc=5 | C=1
- **Notes:** Câu trả lời 'Không đủ dữ liệu' không bám vào ngữ cảnh nào và không cung cấp thông tin liên quan đến quy trình hoàn tiền đã được mô tả.

