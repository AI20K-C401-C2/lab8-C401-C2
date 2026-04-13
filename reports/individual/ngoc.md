# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Bùi Minh Ngọc  
**Vai trò trong nhóm:** Evaluation Owner + Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong Lab này, với vai trò Evaluation Owner và Documentation Owner, tôi tập trung chính vào Sprint 4: Đánh giá và so sánh hiệu suất pipeline RAG. Tôi đã triển khai toàn bộ module `eval.py` theo kiến trúc LLM-as-Judge, chấm điểm tự động theo bốn tiêu chí — Faithfulness, Answer Relevance, Context Recall và Completeness — bằng cách gửi prompt tới `gpt-4o-mini` và nhận về điểm số từ 1–5 kèm lý do. Quyết định kỹ thuật cốt lõi của tôi là thiết kế Context Recall theo cơ chế xác định (string match với `expected_sources`) thay vì dùng LLM để đo, giúp metric này ổn định và không bị ảnh hưởng bởi variance của judge. Ngoài ra, tôi xây dựng logic A/B comparison — tổng hợp delta từng metric, xác định winner và in bảng per-question — để nhóm có bằng chứng định lượng khi quyết định variant nào tốt hơn. Về tài liệu, tôi soạn `docs/architecture.md` mô tả toàn bộ kiến trúc pipeline và điền đầy đủ số liệu thực tế vào `docs/tuning-log.md`. Phần việc này đóng vai trò "gương phản chiếu" toàn bộ pipeline — nếu sprint nào có lỗi, scorecard sẽ phản ánh ngay và tài liệu giúp nhóm truy nguyên nguyên nhân có hệ thống.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Qua lab này, tôi hiểu rõ hơn về sự khác biệt thực chất giữa Context Recall và Faithfulness — hai metrics có vẻ đo cùng một thứ nhưng thực ra hoàn toàn khác nhau. Context Recall đo chất lượng của retriever: liệu hệ thống có lấy đúng tài liệu nguồn không. Faithfulness đo chất lượng của generator: liệu câu trả lời có bám sát vào context đã retrieve không. Trong kết quả của nhóm, Context Recall đạt 5.00/5 nhưng Faithfulness chỉ 3.7/5 vì model đôi khi tự bổ sung thông tin ngoài context — đặc biệt rõ ở q06 khi baseline trả lời lạc sang quy trình cấp quyền thay vì quy trình escalation. Việc gắn metadata chi tiết (source, section, chunk_type) vào từng khối dữ liệu cũng là bài học thực tế quý giá; nó giúp Context Recall đo được chính xác tài liệu nào là nguồn tin đúng, từ đó phân biệt được retrieval fail hay generation fail một cách rõ ràng, thay vì chỉ nhìn vào điểm tổng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều khiến tôi ngạc nhiên nhất là khi chạy `eval.py` lần đầu, toàn bộ 10 câu đều trả về `PIPELINE_ERROR: Collection [rag_lab] does not exist` — điểm số đều là 1/5, không có thông tin gì để phân tích. Tôi phải trace ngược từ `eval.py` → `rag_answer.py` → `index.py` và tìm ra bốn lỗi tích lũy từ quá trình merge code: `get_embedding()` bị SyntaxError do hai đoạn code chồng nhau; `_split_by_size()` chứa dead code sliding-window bị reset bởi `chunks = []` ngay sau — code thực thi thật là paragraph-based theo `\n\n`, overlap thực tế bằng 0; `rerank()` bị định nghĩa hai lần khiến Python chỉ giữ phiên bản đơn giản hơn; và 15 dòng dead code xuất hiện sau `return` trong `retrieve_dense()`. Điều tôi không ngờ là ba lỗi cuối không bị phát hiện bởi `python -m py_compile` vì không phải lỗi cú pháp — phải chạy thực tế mới thấy. Giả thuyết ban đầu của tôi là lỗi nằm ở cấu hình ChromaDB, nhưng sau khi kiểm tra kỹ lưỡng, tôi nhận ra vấn đề gốc rễ nằm ở bước merge code thiếu kiểm tra.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"ERR-403-AUTH là lỗi gì và cách xử lý?"* (id: q09)

Đây là câu hỏi thuộc nhóm "Insufficient Context" nhằm kiểm thử khả năng từ chối trả lời (abstain) của hệ thống. Không có file nào trong `data/docs/` đề cập đến mã lỗi ERR-403-AUTH, nên câu trả lời đúng là "Không đủ dữ liệu."

Baseline và Variant đều abstain đúng (F=1, R=1, Rc=N/A, C=1 — điểm thấp là kỳ vọng vì không có context để verify, không phải vì trả lời sai). Tuy nhiên, câu này vẫn đáng phân tích vì nó thể hiện rủi ro tiềm ẩn: Dense retrieval vẫn truy xuất các chunk có ngữ nghĩa "gần giống" như phân quyền hay bảo mật IT. Nếu prompt không đủ chặt về ABSTAIN rule, LLM có thể bị "ám thị" bởi các ngữ cảnh liên quan và suy luận lỗi 403 là lỗi truy cập dựa trên kiến thức nền — đây là hallucination điển hình, vi phạm nguyên tắc grounding. Với Variant Hybrid, BM25 trả về score 0 cho "ERR-403-AUTH" do không có keyword match; tín hiệu rõ ràng này khi kết hợp với Dense giúp hệ thống xác định chắc chắn hơn là thông tin không tồn tại trong tài liệu, hỗ trợ LLM abstain đúng đắn hơn trong corpus lớn hơn ở tương lai.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ triển khai bước re-ranking bằng Cross-Encoder kết hợp với multi-run aggregation cho LLM judge. Tôi chọn cải tiến này vì kết quả evaluation cho thấy q06 (Escalation P1) có Completeness chỉ đạt 2/5 ở Baseline do chunk đúng bị đẩy xuống vị trí thấp (lost-in-middle effect) — Cross-Encoder sẽ chấm lại relevance từng chunk và đặt chunk quan trọng nhất lên đầu context. Đồng thời, tôi nhận ra LLM judge có variance nhỏ nhưng đáng kể khi delta A/B dưới 0.2, nên chạy mỗi câu 3 lần và lấy median sẽ cho kết luận so sánh đáng tin cậy hơn.
