# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Việt Anh  
**Vai trò trong nhóm:** Tech lead  
**Ngày nộp:** 13/4/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong Lab này, với vai trò Tech Lead, tôi tập trung chính vào Sprint 1: Xây dựng RAG Index. Tôi đã triển khai module tiền xử lý bằng Regex để bóc tách metadata và làm sạch văn bản thô hiệu quả. Quyết định kỹ thuật cốt lõi của tôi là áp dụng chiến lược **Parent-Child Chunking**: coi mỗi Section là Khối Cha để giữ ngữ cảnh và các đoạn văn là Khối Con để tăng độ chính xác khi tìm kiếm. Ngoài ra, tôi đã cấu hình OpenAI Embedding (`text-embedding-3-small`) và lưu trữ dữ liệu vào ChromaDB. Phần việc này đóng vai trò là "xương sống" cho pipeline; dữ liệu được index theo phân tầng giúp Retrieval Owner dễ dàng thực hiện tìm kiếm ở các Sprint tiếp theo và tạo điều kiện cho Tech Lead triển khai logic trả lời có trích dẫn chính xác nhất.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Qua lab này, tôi đã hiểu rõ hơn về tầm quan trọng của chiến lược **chunking** trong hệ thống RAG. Thay vì chia nhỏ văn bản một cách ngẫu nhiên theo số lượng ký tự, tôi đã triển khai chiến lược **Parent-Child** kết hợp với việc cắt theo ranh giới đoạn văn (\n\n) và đề mục (section). Cách tiếp cận này giúp duy trì tính liên kết logic của thông tin, đảm bảo các điều khoản không bị cắt đôi một cách vô nghĩa, dẫn đến sai lệch khi LLM đọc ngữ cảnh. Việc gắn metadata chi tiết (source, section, chunk_type) vào từng khối dữ liệu cũng là một bài học thực tế quý giá; nó giúp bộ lọc retrieval hoạt động chính xác hơn và cho phép hệ thống trích dẫn nguồn (citation) một cách minh bạch, tạo lòng tin cho người dùng khi đối soát với văn bản gốc.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên nhất trong quá trình làm lab là sự nhạy cảm của hệ thống RAG đối với chất lượng dữ liệu đầu vào. Ban đầu, tôi cho rằng chỉ cần cắt văn bản thành các đoạn có độ dài cố định là đủ, nhưng thực tế cho thấy việc này dẫn đến nhiều lỗi nghiêm trọng. Cụ thể, khi áp dụng chunking dựa trên số ký tự, nhiều điều khoản quan trọng bị cắt ngang, làm mất đi ngữ cảnh và khiến LLM không thể hiểu đúng ý nghĩa. Điều này dẫn đến điểm số thấp về Faithfulness và Completeness trong evaluation. Việc debug lỗi này tốn khá nhiều thời gian vì nó không hiển thị ngay lập tức mà chỉ xuất hiện khi chạy bộ test. Giả thuyết ban đầu của tôi là lỗi nằm ở mô hình LLM, nhưng sau khi kiểm tra kỹ lưỡng, tôi nhận ra vấn đề gốc rễ nằm ở bước indexing và chunking.

---

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** ERR-403-AUTH là lỗi gì và cách xử lý? (id: q09)
 
 **Phân tích:**
 Đây là một câu hỏi thuộc nhóm "Insufficient Context" (thiếu thông tin) nhằm kiểm thử khả năng từ chối trả lời (abstain) của hệ thống. 
 - **Baseline (Dense Retrieval):** Với tìm kiếm vector đơn thuần, hệ thống có xu hướng truy xuất các đoạn văn bản có ngữ nghĩa "gần giống" như quy trình cấp quyền hoặc bảo mật IT mặc dù không chứa mã lỗi cụ thể này. Nếu Prompt không đủ chặt chẽ, LLM có thể bị "ám thị" bởi các ngữ cảnh liên quan đến phân quyền và cố gắng suy luận lỗi 403 là lỗi truy cập dựa trên kiến thức nền (hallucination), dẫn đến vi phạm nguyên tắc Grounding và nhận điểm Faithfulness thấp trong scorecard.
 - **Lỗi nằm ở:** Cả khâu Retrieval (không nhận diện được sự vắng mặt của keyword) và Generation (LLM chưa tuân thủ tuyệt đối việc chỉ trả lời từ context).
 - **Cải thiện:** Trong phương án Variant sử dụng **Hybrid Retrieval** (Dense + BM25), công cụ BM25 sẽ trả về điểm số 0 cho từ khóa "ERR-403-AUTH" do không có keyword match. Tín hiệu này khi kết hợp với kết quả Dense sẽ giúp hệ thống xác định rõ ràng hơn là thông tin không tồn tại trong tài liệu nội bộ, từ đó giúp LLM thực hiện hành động "abstain" chuẩn xác hơn, nâng cao độ tin cậy cho trợ lý IT Helpdesk.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ triển khai bước **Self-Correction** và **Re-ranking** sử dụng mô hình Cross-Encoder. Tôi chọn cải tiến này vì kết quả evaluation cho thấy hệ thống vẫn còn gặp khó khăn trong việc từ chối trả lời (abstain) một cách dứt khoát khi gặp các mã lỗi lạ (như câu q09), dẫn đến điểm Faithfulness chưa đạt mức tuyệt đối. Việc sử dụng Cross-Encoder sẽ giúp lọc bỏ các đoạn văn bản gây nhiễu từ bước retrieval, đảm bảo LLM chỉ nhận được những thông tin thực sự có giá trị, từ đó giảm thiểu tình trạng suy luận thiếu căn cứ và tăng cường độ tin cậy cho câu trả lời.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
