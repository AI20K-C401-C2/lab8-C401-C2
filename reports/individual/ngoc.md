# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Bùi Minh Ngọc  
**Vai trò trong nhóm:** Evaluation Owner + Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong Lab này, với vai trò Evaluation Owner và Documentation Owner, tôi tập trung chính vào **Sprint 4: Đánh giá pipeline RAG**. Tôi đã triển khai toàn bộ module `eval.py` theo kiến trúc **LLM-as-Judge**: mỗi câu hỏi trong bộ test được chạy qua hai pipeline (Baseline Dense và Variant Hybrid), sau đó chấm điểm tự động theo bốn metrics — Faithfulness, Answer Relevance, Context Recall và Completeness — với mỗi metric có một prompt riêng gửi đến `gpt-4o-mini` và nhận về JSON `{"score": 1-5, "reason": "..."}`.

Quyết định kỹ thuật cốt lõi của tôi là thiết kế **Context Recall** theo cơ chế deterministic (partial string match với `expected_sources`) thay vì dùng LLM để đo, giúp metric này ổn định và không bị ảnh hưởng bởi variance của judge. Bên cạnh chấm điểm, tôi cũng xây dựng logic **A/B comparison** — tổng hợp delta từng metric giữa baseline và variant, xác định winner theo ngưỡng 0.1 điểm, và in ra bảng per-question để truy vết câu nào cải thiện. Output cuối gồm 4 file: `scorecard_baseline.md`, `scorecard_variant.md`, `ab_comparison.csv` và `grading_run.json`.

Về tài liệu kỹ thuật, tôi soạn `docs/architecture.md` mô tả toàn bộ kiến trúc pipeline (kèm sơ đồ Mermaid và ASCII art) và điền đầy đủ số liệu thực tế vào `docs/tuning-log.md`. Phần việc này đóng vai trò "gương phản chiếu" toàn bộ pipeline — nếu sprint nào có lỗi, scorecard sẽ phản ánh ngay, và tài liệu giúp nhóm truy nguyên nguyên nhân có hệ thống.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Qua lab này, tôi hiểu rõ hơn về sự khác biệt thực chất giữa các metrics đánh giá RAG mà trước đây tôi thường nhầm lẫn. **Context Recall** và **Faithfulness** nghe có vẻ đo cùng một thứ, nhưng thực ra hoàn toàn khác nhau: Context Recall đo chất lượng của *retriever* — liệu hệ thống có lấy đúng tài liệu nguồn không — trong khi Faithfulness đo chất lượng của *generator* — liệu câu trả lời có bám sát vào context đã retrieve không. Trong kết quả của nhóm, Context Recall đạt 5.00/5 (retriever lấy đúng nguồn) nhưng Faithfulness chỉ 3.7/5 vì model đôi khi bổ sung thông tin ngoài context — đặc biệt rõ ở q06 khi baseline trả lời lạc sang quy trình cấp quyền thay vì quy trình escalation.

Điều thú vị hơn là tôi nhận ra **LLM judge không ổn định tuyệt đối** dù đặt `temperature=0`. Khi chạy eval hai lần liên tiếp với cùng input, điểm Faithfulness của một số câu dao động ±1. Điều này khiến tôi hiểu tại sao trong thực tế người ta thường chạy evaluation nhiều lần và lấy trung bình, hoặc phải bổ sung các metrics deterministic song song với LLM-as-Judge để đảm bảo kết luận A/B đáng tin cậy.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều khó khăn nhất trong lab này không phải là viết code eval, mà là phải **debug ngược từ kết quả sai về nguyên nhân gốc rễ**. Khi chạy `eval.py` lần đầu, toàn bộ 10 câu trả về `PIPELINE_ERROR: Collection [rag_lab] does not exist` — điểm số đều là 1/5, không có thông tin gì để phân tích. Tôi phải trace ngược từ `eval.py` → `rag_answer.py` → `index.py` và tìm ra bốn lỗi tích lũy từ quá trình merge code:

1. **`index.py` — SyntaxError tại `get_embedding()`**: Hai đoạn code chồng nhau do merge không sạch — một dòng `response = client.embeddings.create(` bị bỏ dở giữa chừng, làm mở ngoặc không đóng.
2. **`index.py` — Dead code sliding-window trong `_split_by_size()`**: Hàm chứa hai implementations — phần đầu là sliding-window với overlap, phần sau reset `chunks = []` và dùng paragraph-based. Vì bị reset, phần sliding-window không bao giờ có tác dụng; code thực thi là paragraph-based theo `\n\n`, overlap thực tế = 0.
3. **`rag_answer.py` — Hàm `rerank()` định nghĩa hai lần**: Python giữ định nghĩa sau cùng (chỉ return `candidates[:top_k]`), làm mất logic cross-encoder đã implement.
4. **`rag_answer.py` — Dead code sau `return` trong `retrieve_dense()`**: 15 dòng code không bao giờ chạy.

Điều tôi không ngờ là lỗi 2, 3, 4 không bị phát hiện bởi `python -m py_compile` — phải chạy thực tế mới thấy. Bài học: sau mỗi lần merge cần đọc diff cẩn thận, không chỉ kiểm tra compile.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"ERR-403-AUTH là lỗi gì và cách xử lý?"* (id: q09)

**Kết quả:** Baseline F=1, R=1, Rc=N/A, C=1. Variant F=1, R=1, Rc=N/A, C=1.

Đây là câu thuộc nhóm **"Insufficient Context"** — được thiết kế để kiểm tra khả năng **abstain** (từ chối trả lời) của hệ thống khi không có thông tin trong tài liệu. Không có file nào trong `data/docs/` đề cập đến mã lỗi ERR-403-AUTH, vì vậy `expected_sources = []` và câu trả lời đúng là "Không đủ dữ liệu."

Cả hai pipeline đều abstain đúng cách, nên điểm thấp (F=1, R=1) là *kỳ vọng*, không phải lỗi — judge chấm 1 vì không có context để verify, không phải vì trả lời sai. Tuy nhiên, câu này vẫn đáng phân tích vì nó thể hiện **rủi ro tiềm ẩn**: với Baseline Dense, vector search vẫn truy xuất các chunk có ngữ nghĩa "gần" như phân quyền hay bảo mật IT — nếu prompt không đủ chặt về ABSTAIN rule, LLM có thể bị "ám thị" và suy luận lỗi 403 là lỗi truy cập dựa trên model knowledge (hallucination).

Lỗi tiềm năng nằm ở cả **Retrieval** (Dense không phân biệt được sự vắng mặt của exact keyword) và **Generation** (LLM chưa tuân thủ tuyệt đối grounding rule). Với Variant Hybrid, BM25 trả về score = 0 cho "ERR-403-AUTH" vì không có keyword match — tín hiệu này khi kết hợp với Dense giúp hệ thống xác định rõ hơn là thông tin không tồn tại, từ đó hỗ trợ LLM abstain chắc chắn hơn về mặt lý thuyết. Trong kết quả thực tế của nhóm, cả hai đều xử lý đúng, nhưng Hybrid cung cấp tín hiệu retrieval mạnh hơn để phòng ngừa hallucination ở corpus lớn hơn.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ triển khai bước **Re-ranking bằng Cross-Encoder** trước khi đưa chunks vào prompt. Tôi chọn cải tiến này vì kết quả eval cho thấy **q06 (Escalation P1)** — Baseline trả về thông tin về cấp quyền khẩn cấp thay vì quy trình escalation 10 phút, nguyên nhân là chunk đúng bị đẩy xuống vị trí thấp trong top-3 (lost-in-middle effect). Cross-Encoder sẽ chấm lại relevance từng chunk so với query, đảm bảo chunk chứa "10 phút escalation" được đặt lên đầu context — từ đó Completeness kỳ vọng tăng mà không cần thay đổi retrieval hay generation logic. Đây là cải tiến có evidence từ scorecard, không phải cải thiện chung chung.
