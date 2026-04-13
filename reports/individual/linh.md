# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thùy Linh  
**Vai trò trong nhóm:** Retrieval Owner (Sprint 2 — Dense Retrieval)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong Lab này, với vai trò Retrieval Owner, tôi tập trung chính vào Sprint 2: Triển khai Dense Retrieval — bước cầu nối giữa ChromaDB index (Sprint 1) và generation layer. Tôi đã implement toàn bộ hàm `retrieve_dense()` trong `rag_answer.py`: nhận query từ người dùng, embed bằng cùng model `text-embedding-3-small` đã dùng khi index, truy vấn ChromaDB với `n_results=top_k` và nhận về `documents`, `metadatas`, `distances`. Quyết định kỹ thuật cốt lõi là chuyển đổi kết quả từ `distance → similarity` theo công thức `similarity = 1 - distance`, vì ChromaDB cosine space lưu distance (không phải similarity), sau đó sort giảm dần để đảm bảo chunk relevant nhất luôn ở đầu danh sách. Ngoài ra, tôi triển khai hàm `select_sources()` — trích xuất danh sách source duy nhất theo đúng thứ tự xuất hiện bằng `seen` set, tránh để citation bị đảo thứ tự ngẫu nhiên như khi dùng set comprehension. Phần việc này là "đầu vào" cho toàn bộ pipeline — nếu retrieve sai chunk, generation layer sẽ không có đủ dữ liệu và evaluation sẽ ghi nhận Context Recall thấp ngay lập tức.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Qua lab này, tôi hiểu rõ hơn về cơ chế hoạt động thực tế của vector search trong ChromaDB — điều mà trước đây tôi chỉ hiểu ở mức lý thuyết. Điểm quan trọng nhất là ChromaDB với `hnsw:space = cosine` lưu trữ cosine distance (không phải similarity), trả về giá trị từ 0 đến 2, trong đó 0 nghĩa là hoàn toàn giống nhau. Nếu không chuyển đổi, danh sách chunk sau khi sort sẽ bị đảo ngược — chunk ít relevant nhất lại được đưa vào prompt đầu tiên, gây ra lỗi rất khó debug vì pipeline vẫn chạy bình thường, chỉ cho câu trả lời sai. Tôi cũng hiểu rõ hơn tầm quan trọng của thứ tự trong citation: khi dùng set comprehension để thu thập sources, thứ tự không được đảm bảo nên `[2]` có thể xuất hiện trước `[1]` trong câu trả lời. Hàm `select_sources()` với `seen` set giải quyết vấn đề này, tạo sự nhất quán giữa context block và citation mà LLM tạo ra.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều khiến tôi ngạc nhiên nhất là độ nhạy cảm của ChromaDB với kiểu dữ liệu đầu vào. Ban đầu tôi truyền `top_k` trực tiếp vào `n_results` mà không kiểm tra, dẫn đến lỗi `ValueError: n_results must be a positive integer` khi `top_k` được truyền vào dưới dạng float (ví dụ `10.0` thay vì `10`). Lỗi này không xuất hiện trong quá trình phát triển vì tôi test với giá trị integer, nhưng lại bùng phát khi `eval.py` gọi pipeline với config dict. Fix rất đơn giản — thêm `n_results = max(1, int(top_k))` — nhưng mất thời gian debug vì traceback chỉ trỏ vào ChromaDB internals. Khó khăn thứ hai là merge conflict với code của Trường. Sau khi merge, hàm `rerank()` bị định nghĩa hai lần và dead code xuất hiện sau `return` trong `retrieve_dense()`. Giả thuyết ban đầu của tôi là lỗi nằm ở phần embedding, nhưng sau khi kiểm tra kỹ lưỡng từng hàm, tôi nhận ra vấn đề gốc rễ nằm ở quá trình merge thiếu kiểm soát diff.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"* (id: q07)

Đây là câu thú vị nhất từ góc nhìn của Retrieval Owner vì nó phơi bày kịch bản mà retriever thành công nhưng pipeline vẫn thất bại. Context Recall = 5 ở cả hai pipeline — `retrieve_dense()` và `retrieve_hybrid()` đều lấy đúng file `access_control_sop.txt`. Về mặt kỹ thuật, phần tôi làm đã hoạt động đúng. Tuy nhiên, query dùng alias cũ "Approval Matrix" trong khi tài liệu chỉ đề cập đến "Access Control SOP". Dense retrieval xử lý tốt vì embedding nắm bắt được ngữ nghĩa liên quan, nhưng generation layer lại abstain — model nhận được context về "Access Control SOP" nhưng không nhận ra đây là câu trả lời cho câu hỏi về "Approval Matrix". Lỗi hoàn toàn nằm ở generation layer, không phải retrieval. Kể cả Hybrid (BM25 thêm keyword matching) cũng không giúp được vì vấn đề không phải là keyword mismatch trong corpus mà là LLM không kết nối được alias với tên hiện tại. Cải thiện đúng ở đây là thêm query expansion: dùng LLM để sinh alias trước khi retrieve, ví dụ "Approval Matrix" → "Access Control SOP", "access control document" — đây là cải tiến thuộc query transformation layer.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ triển khai lọc parent chunk trong `retrieve_dense()`. Hiện tại ChromaDB trả về cả Parent chunk và Child chunk lẫn lộn trong top-k results. Parent chunk chứa toàn bộ nội dung một section — nếu lọt vào prompt sẽ làm context quá dài và gây lost-in-middle effect. Tôi chọn cải tiến này vì kết quả eval cho thấy Completeness của một số câu chưa đạt tối đa, nguyên nhân có thể một phần do Parent chunk chiếm slot trong top-3, đẩy Child chunk chứa thông tin cụ thể ra ngoài context. Fix chỉ cần một dòng: `candidates = [c for c in results if c["metadata"].get("chunk_type") != "parent"]` — chi phí thấp nhưng kỳ vọng cải thiện Completeness rõ rệt.
