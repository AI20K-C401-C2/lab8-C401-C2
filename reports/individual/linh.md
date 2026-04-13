# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thị Linh  
**Vai trò trong nhóm:** Retrieval Owner (Sprint 2 — Dense Retrieval)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong Lab này, với vai trò Retrieval Owner, tôi tập trung chính vào **Sprint 2: Triển khai Dense Retrieval và kết nối pipeline RAG**. Nhiệm vụ cốt lõi của tôi là implement hàm `retrieve_dense()` trong `rag_answer.py` — bước "cầu nối" giữa ChromaDB index (Sprint 1) và generation layer (Sprint 2b).

Cụ thể, tôi đã triển khai toàn bộ logic dense retrieval: nhận query từ người dùng, embed bằng cùng model `text-embedding-3-small` đã dùng khi index, sau đó query ChromaDB với `n_results=top_k` và nhận về `documents`, `metadatas`, `distances`. Một quyết định kỹ thuật quan trọng là chuyển đổi `distance → similarity` theo công thức `similarity = 1 - distance` (do ChromaDB cosine space lưu distance, không phải similarity), rồi sort giảm dần theo score để đảm bảo chunk relevant nhất luôn ở đầu danh sách.

Ngoài `retrieve_dense()`, tôi cũng implement hàm `select_sources()` — trích xuất danh sách source duy nhất từ top chunks **theo đúng thứ tự xuất hiện** (dùng `seen` set thay vì tập hợp thông thường để giữ thứ tự ưu tiên), phục vụ cho việc hiển thị citation trong câu trả lời. Tôi cũng cải thiện phần `rag_answer()`: thêm `n_select = max(1, int(top_k_select))` để tránh lỗi khi top_k_select không hợp lệ, và thay thế set comprehension nguồn gốc (`{c["metadata"].get("source")}`) bằng lời gọi `select_sources()` để đảm bảo thứ tự citation nhất quán.

Công việc của tôi là "xương sống" cho retrieval — nếu `retrieve_dense()` không trả về đúng chunks, toàn bộ generation layer (Trường C) sẽ không có đủ context để trả lời, và evaluation layer (Ngọc) sẽ ghi nhận Context Recall thấp.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Qua lab này, tôi hiểu rõ hơn về cơ chế hoạt động thực tế của **vector search trong ChromaDB** — điều mà trước đây tôi chỉ hiểu ở mức lý thuyết. Điểm quan trọng nhất là ChromaDB với `hnsw:space = cosine` lưu trữ **cosine distance** (không phải similarity), trả về giá trị từ 0 đến 2, trong đó 0 nghĩa là hoàn toàn giống nhau. Nếu không chuyển đổi `similarity = 1 - distance`, danh sách chunk sau khi sort sẽ bị đảo ngược — chunk ít relevant nhất lại được đưa vào prompt đầu tiên, gây ra lỗi rất khó debug vì pipeline vẫn chạy bình thường.

Tôi cũng hiểu rõ hơn tầm quan trọng của **thứ tự trong citation**. Khi dùng set comprehension để thu thập sources, thứ tự không được đảm bảo — citation `[2]` có thể xuất hiện trước `[1]` trong câu trả lời. Hàm `select_sources()` với `seen` set giải quyết vấn đề này: source nào xuất hiện trong top chunk đầu tiên sẽ được đánh số `[1]`, tạo sự nhất quán giữa context block và citation trong câu trả lời của LLM.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều khiến tôi ngạc nhiên nhất là **độ nhạy cảm của ChromaDB với kiểu dữ liệu đầu vào**. Ban đầu tôi truyền `top_k` trực tiếp vào `n_results` mà không kiểm tra, dẫn đến lỗi `ValueError: n_results must be a positive integer` khi `top_k` được truyền vào dưới dạng float (ví dụ `10.0` thay vì `10`). Lỗi này không xuất hiện trong quá trình phát triển vì tôi test với giá trị integer, nhưng xuất hiện khi `eval.py` gọi pipeline với config dict. Fix rất đơn giản — thêm `n_results = max(1, int(top_k))` — nhưng mất thời gian debug vì traceback chỉ trỏ vào ChromaDB internals.

Khó khăn thứ hai là **merge conflict với code của Trường C**. Cả hai chúng tôi đều chỉnh sửa `rag_answer.py` — tôi thêm `retrieve_dense()` và `select_sources()`, Trường C thêm `build_grounded_prompt()` và `call_llm()`. Sau khi merge, hàm `rerank()` bị định nghĩa hai lần (một lần có cross-encoder, một lần chỉ return `candidates[:top_k]`) và dead code xuất hiện sau `return` trong `retrieve_dense()`. Đây là bài học về việc cần phân chia file rõ ràng hơn hoặc dùng feature branch riêng biệt cho từng hàm.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"* (id: q07)

**Kết quả:** Baseline F=1, R=1, Rc=5, C=1. Variant F=1, R=1, Rc=5, C=1.

Đây là câu thú vị nhất từ góc nhìn của Retrieval Owner vì nó phơi bày một **kịch bản mà retriever thành công nhưng pipeline vẫn thất bại**. Context Recall = 5 ở cả hai pipeline — `retrieve_dense()` và `retrieve_hybrid()` đều lấy đúng file `access_control_sop.txt`. Điều đó có nghĩa là về mặt kỹ thuật, phần tôi làm đã hoạt động đúng.

Tuy nhiên, query dùng alias cũ **"Approval Matrix"** trong khi tài liệu chỉ đề cập đến **"Access Control SOP"**. Dense retrieval xử lý tốt vì embedding nắm bắt được ngữ nghĩa liên quan (cả hai đều về phân quyền hệ thống). Nhưng generation layer lại abstain — model nhận được context về "Access Control SOP" nhưng không nhận ra đây là câu trả lời cho câu hỏi về "Approval Matrix", nên trả lời "Không đủ dữ liệu."

Lỗi hoàn toàn nằm ở **generation layer**, không phải retrieval. Kể cả Hybrid (BM25 thêm keyword matching) cũng không giúp được vì vấn đề không phải là keyword mismatch trong corpus mà là LLM không kết nối được alias với tên hiện tại. Fix đúng ở đây là thêm query expansion trước bước retrieve: dùng LLM để sinh alias *"Approval Matrix" → ["Access Control SOP", "access control document"]* — đây là cải tiến thuộc query transformation layer, không phải retrieval layer.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ triển khai **lọc parent chunk** trong `retrieve_dense()`. Hiện tại ChromaDB trả về cả Parent chunk và Child chunk lẫn lộn trong top-k results. Parent chunk chứa toàn bộ nội dung một section — nếu lọt vào prompt sẽ làm context quá dài (lost-in-middle effect). Tôi sẽ thêm một bước filter: `candidates = [c for c in results if c["metadata"].get("chunk_type") != "parent"]` trước khi return. Kết quả eval của nhóm cho thấy Completeness của một số câu chưa đạt tối đa — nguyên nhân có thể một phần do Parent chunk chiếm slot trong top-3, đẩy Child chunk chứa thông tin cụ thể hơn ra ngoài context.
