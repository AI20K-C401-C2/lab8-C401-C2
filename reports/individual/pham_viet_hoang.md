# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Việt Hoàng  
**MSSV:** 2A202600274  
**Vai trò trong nhóm:** Git Merge Lead & Code Integration Fixer  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab Day 08, tôi đảm nhận vai trò **Git Merge Lead** — chịu trách nhiệm tích hợp code từ nhiều nhánh cá nhân (linh, truong, minh, ngoc) về nhánh `main` và đảm bảo pipeline chạy end-to-end không bị lỗi sau mỗi lần merge.

Cụ thể, tôi đã thực hiện:
- **Resolve merge conflicts** trong `rag_answer.py`: khi nhánh của Minh (variant hybrid) merge vào nhánh của Linh (dense retrieval), xảy ra xung đột ở hàm `rerank()` bị định nghĩa hai lần và dead code xuất hiện sau `return` trong `retrieve_dense()`. Tôi đã dùng `git diff` để so sánh hai phiên bản, giữ lại implementation đầy đủ của Minh và xóa bản duplicate ngắn gọn hơn bị sinh ra do merge conflict auto-resolution.
- **Fix syntax errors từ code chồng chéo**: sau một lần merge, `get_embedding()` bị SyntaxError do hai đoạn code từ nhánh khác nhau bị dán chồng lên nhau. Tôi đã tách riêng phần `load_dotenv()` và logic chọn model OpenAI/SentenceTransformer cho rõ ràng.
- **Kiểm tra tính hợp lệ trước khi push**: mỗi lần merge xong, tôi chạy `python -m py_compile index.py rag_answer.py eval.py` và chạy thử `python index.py` để đảm bảo không có lỗi cú pháp ẩn. Đây là lý do pipeline cuối cùng có thể chạy end-to-end mà không crash.

Phần việc của tôi không tạo ra feature mới nhưng là "chốt chặn" cuối cùng để code từ nhiều ngườ không bị phá vỡ khi hợp nhất.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Trước đây tôi nghĩ Git merge chỉ là chọn "ours" hay "theirs" rồi xong. Lab này cho tôi thấy **merge conflict resolution là một kỹ năng đọc hiểu code** — đặc biệt khi cùng một hàm `rerank()` xuất hiện ở hai vị trí khác nhau trong file, chọn sai sẽ làm mất cả logic cross-encoder hoặc RRF.

Tôi cũng hiểu rõ hơn về **"silent failures"** trong Python: dead code đặt sau `return` không gây SyntaxError, nhưng sẽ khiến ngườ khác tưởng logic đó có hiệu lực. Điều này rất nguy hiểm trong teamwork vì `python -m py_compile` không bắt được, phải chạy thực tế mới thấy behavior sai. Từ đó tôi thiết lập thói quen chạy smoke test sau mỗi merge, dù chỉ là thay đổi nhỏ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất là debug **"merge ghost"** — những đoạn code xuất hiện mà không ai cố ý viết. Ví dụ, sau merge giữa nhánh `dev` và `minh`, `rag_answer.py` có 15 dòng code nằm sau `return` trong `retrieve_dense()`. Cả Linh và Minh đều không viết đoạn code đó ở vị trí đó; nó được Git sinh ra do marker conflict bị xử lý không sạch. Tôi mất gần 20 phút để trace từng nhánh xem đoạn code này từ đâu ra.

Điều ngạc nhiên thứ hai là merge conflict không chỉ xảy ra ở code mà còn ở **config dictionary** trong `eval.py`. Hai nhánh cùng sửa `VARIANT_CONFIG` — một nhánh đổi `retrieval_mode` thành `"hybrid"`, nhánh khác đổi `use_rerank` thành `True` — khi merge, Git báo conflict ở đúng một dòng `use_rerank`. Nếu chọn một trong hai, pipeline sẽ chạy với config không đúng ý định của nhóm. Tôi phải hỏi trực tiếp Minh và Ngọc để xác nhận variant cuối cùng là hybrid không rerank.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"Escalation trong sự cố P1 diễn ra như thế nào?"* (id: q06)

**Phân tích:**

- **Baseline (dense):** Completeness = 2/5. Pipeline trả lờ về quy trình cấp quyền tạm thờ cho on-call IT Admin (24 giờ, Tech Lead phê duyệt) nhưng **bỏ sót hoàn toàn** quy trình escalate lên Senior Engineer sau 10 phút không phản hồi. Điều này xảy ra vì chunk chứa thông tin escalation nằm ở vị trí thấp trong top-k, bị đẩy ra khỏi top-3 select.

- **Lỗi nằm ở đâu:** Theo góc nhìn integration, lỗi không phải ở một hàm đơn lẻ mà ở **giao diện giữa retrieval và generation**. `retrieve_dense()` trả về đủ 10 chunk, nhưng `select_sources()` và build-context logic không ưu tiên chunk có từ khóa "escalate" / "10 phút". Kết quả là context block gửi vào prompt thiếu evidence quan trọng.

- **Variant (hybrid):** Completeness = 5/5. BM25 bắt chính xác keyword "escalate" và "10 phút", đưa chunk đúng vào top-3. Điều này chứng minh khi hai phần code (dense của Linh + sparse của Minh) được merge đúng cách, pipeline hoạt động tốt hơn rõ rệt. Tuy nhiên, nếu merge sai và BM25 index bị tạo lại mỗi lần query (như bug ban đầu Minh gặp), hiệu quả sẽ giảm đi đáng kể.

---

## 5. Nếu có thêm thờ gian, tôi sẽ làm gì?

Tôi sẽ triển khai **GitHub Actions CI pipeline** cho repo này. Mỗi pull request sẽ tự động chạy `py_compile` trên 3 file Python và một smoke test với 2 câu hỏi mẫu (q01 + q09) để phát hiện merge regression ngay lập tức. Đây là cải tiến thuộc về quy trình teamwork — kết quả eval cho thấy nhiều lỗi không đến từ algorithm mà đến từ code integration, nên CI sẽ tiết kiệm thờ gian debug hơn bất kỳ thuật toán nào.

---
