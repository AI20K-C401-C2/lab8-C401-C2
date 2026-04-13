# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Tuấn Minh 
**Vai trò trong nhóm:** Tuning Owner   
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Tôi đã đóng góp chủ yếu ở Sprint 3
Tôi đảm nhận vai trò Tuning Owner, chịu trách nhiệm chính trong Sprint 3 — implement variant hybrid retrieval để so sánh với baseline dense retrieval.
Cụ thể, tôi đã implement hai hàm chính trong `rag_answer.py`:

- **`retrieve_sparse()`**: Xây dựng BM25 search bằng thư viện `rank_bm25`. Hàm này load toàn bộ chunks từ ChromaDB, tokenize bằng regex (`re.findall(r"\w+", text.lower())`), tạo BM25 index, rồi trả về top-k kết quả theo keyword matching score.

- **`retrieve_hybrid()`**: Kết hợp kết quả từ `retrieve_dense()` và `retrieve_sparse()` bằng thuật toán Reciprocal Rank Fusion (RRF) với công thức `RRF_score = weight * (1 / (60 + rank))`. Dense weight = 0.6, sparse weight = 0.4. Merge hai danh sách kết quả vào một dict chung, sort theo RRF score giảm dần.

Công việc của tôi kết nối trực tiếp với phần Sprint 2 (baseline dense) — hybrid gọi `retrieve_dense()` làm một trong hai nguồn dữ liệu đầu vào.
---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.
Sau lab, tôi hiểu rõ hơn sự khác biệt giữa dense retrieval và sparse retrieval, và tại sao cần kết hợp cả hai.

**Dense retrieval** (embedding similarity) mạnh ở việc hiểu nghĩa — ví dụ query "chính sách nghỉ phép" vẫn match được chunk viết "quy định về annual leave". Nhưng nó yếu với keyword chính xác như mã lỗi "ERR-403" hay "P1".

**Sparse retrieval** (BM25) ngược lại — match chính xác từ khóa rất tốt, nhưng không hiểu paraphrase hay đồng nghĩa.

**Hybrid** kết hợp cả hai bằng RRF — một thuật toán merge đơn giản nhưng hiệu quả. Hằng số 60 trong công thức RRF giúp cân bằng giữa top documents (rank thấp) và documents ở xa hơn, tránh việc rank 1 cách quá xa rank 2 về điểm. Đây là điều tôi chỉ hiểu được khi thực sự code và debug, không phải chỉ đọc slide.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?
Khó khăn lớn nhất là **quản lý Git khi làm nhóm**. Tôi mất khá nhiều thời gian xử lý merge conflict giữa các nhánh. Có lúc merge bị chồng code (2 phiên bản cùng 1 hàm dán chồng nhau), gây syntax error mà phải đọc kỹ mới phát hiện.

Điều ngạc nhiên thứ hai là **key matching trong RRF**. Ban đầu tôi dùng key khác nhau cho dense (`source + hash(text)`) và sparse (`text[:100]`), dẫn đến cùng 1 chunk từ 2 nguồn không được nhận diện là giống nhau ,điểm không cộng dồn , hybrid không khác gì dense. Đây là lỗi logic tinh vi mà chỉ khi phân tích output mới phát hiện được.
_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "SLA xử lý ticket P1 là bao lâu?"

**Phân tích:**
Với **baseline (dense)**, câu hỏi này hoạt động khá tốt vì cụm từ "SLA" và "P1" xuất hiện rõ ràng trong tài liệu `sla_p1_2026`. Dense retrieval có thể match được nghĩa chung của câu hỏi với nội dung tài liệu. Tuy nhiên, do dense dựa vào embedding similarity, khi query ngắn (ít context), kết quả có thể không chính xác — embedding của "SLA P1" có thể gần với nhiều chunk không liên quan.

Với **variant (hybrid)**, sparse/BM25 bắt chính xác keyword "P1" và "SLA" với những chunk chứa đúng từ khóa này được ưu tiên. Kết hợp với dense qua RRF, chunk chứa thông tin SLA P1 xuất hiện ở cả hai nguồn thì điểm RRF cao hơn rồi xếp hạng cao nhất.

Lỗi tiềm ẩn nằm ở **retrieval**: nếu dense trả về chunk từ tài liệu khác (ví dụ HR policy) vì embedding similarity cao nhưng nội dung không liên quan, generation sẽ bị "lost in the middle" hoặc trả lời sai. Hybrid khắc phục bằng việc ưu tiên chunk match cả nghĩa lẫn keyword.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

1. **Sửa key matching trong RRF**: Dùng `chunk["text"][:200]` thống nhất cho cả dense và sparse để đảm bảo cùng 1 chunk được cộng dồn điểm đúng cách. Hiện tại key khác nhau làm giảm hiệu quả fusion.

2. **Cache BM25 index**: Hiện tại mỗi lần gọi `retrieve_sparse()` đều load lại toàn bộ corpus từ ChromaDB và tạo lại BM25 index — rất chậm. Tôi sẽ cache ở module-level để chỉ build 1 lần.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
