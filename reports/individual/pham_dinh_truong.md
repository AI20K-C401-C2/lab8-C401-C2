# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Đình Trường  
**Mã Sinh Viên** 2A202600255
**Vai trò trong nhóm:** Phụ trách rag_answer.py phần generation Làm prompt grounded, citation, abstain  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong dự án xây dựng RAG Pipeline cho trợ lý nội bộ khối CS + IT Helpdesk, tôi tập trung chủ yếu vào **Sprint 2**, chịu trách nhiệm hoàn thiện phần **Generation (Tạo câu trả lời)** trong file `rag_answer.py`. 

Cụ thể, tôi đã thực hiện các công việc:
- Thiết kế **Grounded Prompt**: Xây dựng bộ quy tắc ép LLM chỉ trả lời dựa trên ngữ cảnh cung cấp, tuyệt đối không được tự suy diễn thông tin bên ngoài.
- Cấu hình cơ chế **Citation**: Yêu cầu AI tự động trích dẫn số thứ tự tài liệu như  vào sau mỗi ý chính để tăng tính minh bạch.
- Xử lý **Abstain**: Quy định rõ ràng thông báo phản hồi "Không đủ dữ liệu" khi tài liệu truyền vào không chứa thông tin cần thiết.
- Kết nối mã nguồn: Tích hợp kết quả từ phần Retrieval của nhóm vào luồng xử lý của LLM (OpenAI) để tạo ra đầu ra cuối cùng cho hệ thống

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau bài lab này, tôi đã hiểu rõ hơn về tầm quan trọng của **Grounded Prompting** (Ràng buộc ngữ cảnh). Trước đây, tôi nghĩ AI chỉ cần đọc tài liệu là có thể trả lời đúng, nhưng thực tế AI rất dễ bị "hallucination" (ảo tưởng) và dùng kiến thức cũ của nó để lấp liếm những chỗ tài liệu không có. 

Thông qua việc tinh chỉnh prompt, tôi học được cách thiết lập "hàng rào bảo vệ" (guardrails) chặt chẽ bằng ngôn ngữ tự nhiên. Tôi nhận ra rằng việc ép AI "biết nói không" (Abstain) quan trọng không kém việc bắt nó trả lời đúng, vì trong doanh nghiệp, một câu trả lời sai còn nguy hại hơn một câu trả lời từ chối. Ngoài ra, việc gán ID cho từng chunk văn bản để thực hiện **Citation** giúp tạo ra niềm tin cho người dùng khi họ có thể truy vết nguồn gốc thông tin một cách chính xác.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất mà tôi gặp phải là việc thiết lập môi trường trên Windows, cụ thể là lỗi **UnicodeDecodeError** khi chạy `pip install`. Do file `requirements.txt` chứa ký tự tiếng Việt UTF-8 nhưng terminal lại đọc theo chuẩn CP1252, việc này đã làm tôi mất khá nhiều thời gian để tìm ra cách ép Python chạy theo UTF-8.

Bên cạnh đó, tôi cũng gặp lỗi **Authentication 401** liên tục mặc dù đã có mã API. Sau khi kiểm tra kỹ, lỗi không nằm ở code mà ở việc quản lý file `.env` và cách load biến môi trường. Điều làm tôi ngạc nhiên nhất là sức mạnh của các model nhỏ như `gpt-4o-mini`. Chỉ với một prompt được cấu trúc tốt (structured prompt), model có thể tuân thủ chính xác định dạng trích dẫn và các quy tắc từ chối trả lời mà không cần đến những model khổng lồ, giúp tối ưu chi phí và tốc độ cho hệ thống.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "ERR-403-AUTH là lỗi gì và cách xử lý?" (Mã câu hỏi: `q09`)

**Phân tích:**
Đây là một câu hỏi được thiết kế riêng để kiểm tra khả năng **Abstain** (từ chối trả lời) của hệ thống, vì trong bộ tài liệu 5 file hiện tại (Chính sách hoàn tiền, SLA, SOP cấp quyền...), hoàn toàn không có thông tin về mã lỗi "ERR-403-AUTH".

- **Kết quả Baseline**: Hệ thống đã thực hiện chính xác theo thiết kế. Bước Retrieval không tìm thấy chunk nào thực sự liên quan đến mã lỗi này. 
- **Generation**: Khi Prompt nhận được khối Context trống hoặc không liên quan, định chế "Nếu không có đủ thông tin, hãy trả lời: 'Không đủ dữ liệu'" đã phát huy tác dụng. AI đã không cố gắng giải thích mã lỗi 403 theo kiến thức chung về HTTP mà nó có sẵn.
- **Lỗi nằm ở đâu**: Đây không phải lỗi mà là hành vi mong muốn của hệ thống. Tuy nhiên, nếu muốn AI trả lời được câu này, ta cần bổ sung dữ liệu vào phần **Indexing**. Lỗi lúc này thuộc về **Data Coverage**.
- **Cải thiện**: Trong Sprint 3, nếu chúng ta thêm Hybrid Retrieval (BM25), hệ thống có thể tìm kiếm chính xác các từ khóa mã lỗi tốt hơn, nhưng với câu `q09` này, kết quả vẫn sẽ là từ chối nếu file tài liệu IT helpdesk FAQ chưa được cập nhật chính quy mã lỗi đó.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ triển khai **Hybrid Retrieval (Dense + Sparse)**. Hiện tại hệ thống đang dùng Dense search (Vector), rất tốt cho ý nghĩa nhưng đôi khi "trượt" các từ khóa kỹ thuật chính xác như mã lỗi hoặc tên quy trình viết tắt. Tôi muốn thử thuật toán **Reciprocal Rank Fusion (RRF)** để gộp kết quả từ BM25 và Vector search, vì kết quả đánh giá scorecard hiện nay cho thấy chúng ta vẫn gặp khó khăn với các câu hỏi chứa keyword lạ chưa có trong từ điển của model embedding.

---
