# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Bùi Minh Ngọc  
**Vai trò trong nhóm:** Evaluation Owner + Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi phụ trách **Sprint 4 (Evaluation)** và toàn bộ tài liệu kỹ thuật của nhóm.

Về phía evaluation, tôi hoàn thiện `eval.py` — script chạy 10 câu hỏi qua cả hai pipeline (Baseline Dense và Variant Hybrid), sau đó chấm điểm tự động bằng **LLM-as-Judge** theo 4 metrics: Faithfulness, Answer Relevance, Context Recall và Completeness. Mỗi metric có một prompt riêng gửi đến `gpt-4o-mini` làm judge, trả về JSON `{"score": 1-5, "reason": "..."}`. Ngoài việc chạy pipeline, tôi cũng triển khai logic **A/B comparison** — so sánh từng câu theo 4 metrics và in ra bảng tổng hợp winner. Output cuối gồm 4 file: `scorecard_baseline.md`, `scorecard_variant.md`, `ab_comparison.csv`, và `grading_run.json`.

Về tài liệu, tôi viết `docs/architecture.md` mô tả toàn bộ kiến trúc pipeline từ indexing đến evaluation (kèm sơ đồ Mermaid và ASCII art), và điền đầy đủ số liệu thực tế vào `docs/tuning-log.md` sau khi có kết quả eval.

Công việc của tôi phụ thuộc vào phần retrieval và generation của các thành viên khác — `eval.py` gọi `rag_answer()` từ `rag_answer.py` do các bạn implement. Điều đó có nghĩa là nếu `rag_answer.py` có bug, scorecard sẽ trả về toàn bộ `PIPELINE_ERROR` — và đó chính xác là điều đã xảy ra lúc đầu.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

**LLM-as-Judge và tính không ổn định của nó:** Trước khi làm lab, tôi nghĩ dùng LLM để chấm điểm sẽ cho kết quả nhất quán vì temperature=0. Thực tế thì không hẳn — khi chạy `eval.py` hai lần liên tiếp với cùng input, điểm Faithfulness của q01 lần đầu là 5, lần sau là 4. LLM judge có variance nhỏ nhưng đủ để ảnh hưởng đến kết luận A/B nếu hai pipeline có hiệu suất gần nhau (delta < 0.2). Điều này khiến tôi hiểu tại sao trong thực tế người ta thường chạy evaluation nhiều lần và lấy trung bình, hoặc dùng **deterministic metrics** (như Context Recall mà tôi implement bằng exact/partial string match) song song với LLM-as-Judge.

**Context Recall khác Faithfulness:** Hai metrics này nghe giống nhau nhưng đo hoàn toàn khác thứ. Context Recall đo *retriever* — có lấy đúng tài liệu không (so với `expected_sources`). Faithfulness đo *generator* — câu trả lời có bám vào context đã retrieve không. Trong kết quả của nhóm, Context Recall = 5.00/5 (retriever hoạt động tốt) nhưng Faithfulness chỉ 3.7–3.8/5 vì model đôi khi tự thêm thông tin ngoài context.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất là **bug trong `rag_answer.py` và `index.py`** phát hiện ra khi chạy eval lần đầu — toàn bộ 10 câu đều trả về `PIPELINE_ERROR: Collection [rag_lab] does not exist`. Khi tôi debug, tìm ra ba lỗi tích lũy:

1. `index.py` có **SyntaxError** tại `get_embedding()` — hai đoạn code chồng nhau do merge không sạch, làm mở ngoặc không đóng.
2. `rag_answer.py` định nghĩa hàm `rerank()` **hai lần** — Python chỉ giữ định nghĩa sau cùng (không có cross-encoder), làm mất luôn logic đã implement.
3. `rag_answer.py` có **dead code sau `return`** trong `retrieve_dense()` — 15 dòng code không bao giờ chạy nhưng gây nhầm lẫn khi đọc.

Điều tôi không ngờ là những lỗi này không bị phát hiện bởi `python -m py_compile` (không có lỗi syntax ở file 2 và 3), nên phải chạy thực tế mới thấy. Sau khi fix xong và chạy lại `index.py` để build ChromaDB (58 chunks từ 5 file), `eval.py` mới chạy được end-to-end. Bài học: unit test từng function quan trọng hơn là chờ đến integration test cuối.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi q06:** *"Escalation trong sự cố P1 diễn ra như thế nào?"*

**Kết quả:** Baseline F=5, R=5, Rc=5, **C=2**. Variant F=5, R=5, Rc=5, **C=5**.

Đây là câu thú vị nhất vì Context Recall = 5 ở cả hai — retriever đã lấy đúng tài liệu `sla_p1_2026.txt`. Vậy tại sao Completeness lại chênh nhau đến 3 điểm?

Khi xem câu trả lời thực tế: Baseline trả về thông tin về "On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ)" — đây là thông tin đúng nhưng thuộc về quy trình cấp quyền khẩn cấp, **không phải** quy trình escalation. Expected answer yêu cầu: "tự động escalate lên Senior Engineer nếu không có phản hồi trong **10 phút** sau khi tạo ticket."

Lỗi nằm ở **generation layer**: dense retrieval trả về top-3 chunks, nhưng chunk chứa thông tin "10 phút escalation" bị đẩy xuống thứ tự thấp hơn chunk về cấp quyền. GPT-4o-mini tập trung vào chunk đầu tiên (lost-in-middle effect). Variant hybrid BM25 bắt được keyword "escalate" và "10 phút" chính xác hơn, đẩy chunk đúng lên top-1 → model trả lời đầy đủ hơn → Completeness tăng từ 2 lên 5.

Đây là bằng chứng rõ nhất cho thấy **thứ tự chunk trong context ảnh hưởng lớn đến chất lượng generation** — không chỉ là có/không có thông tin.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

**Ưu tiên 1 — Query expansion cho q07 (alias queries):** Scorecard cho thấy q07 ("Approval Matrix") fail ở cả hai pipeline — F=1, R=1 dù Rc=5 (retriever lấy đúng tài liệu!). Lỗi nằm hoàn toàn ở generation — model nhận được context về "Access Control SOP" nhưng không nhận ra đây là câu trả lời cho "Approval Matrix là tài liệu nào" và chọn abstain. Tôi sẽ thêm một bước pre-processing: dùng LLM sinh 2–3 alias trước khi retrieve, ví dụ: *"Approval Matrix" → ["Access Control SOP", "permission approval document", "system access policy"]*. Chi phí thêm ~1 LLM call nhưng kỳ vọng cải thiện Faithfulness và Completeness cho dạng câu hỏi này.

**Ưu tiên 2 — Multi-run aggregation cho LLM judge:** Chạy mỗi câu 3 lần với judge, lấy median score để giảm variance. Điều này đặc biệt quan trọng khi delta A/B nhỏ (như faithfulness -0.10 của nhóm) — không thể kết luận chắc chắn nếu chỉ chạy 1 lần.
