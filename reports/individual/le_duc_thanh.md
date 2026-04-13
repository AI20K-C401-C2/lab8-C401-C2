# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Đức Thanh  
**MSSV:** 2A202600093  
**Vai trò trong nhóm:** End-to-End Testing Lead  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Với vai trò **End-to-End Testing Lead**, tôi chịu trách nhiệm kiểm thử toàn bộ pipeline từ indexing đến evaluation, đảm bảo các sprint kết nối mượt mà trước khi chạy grading questions.

Cụ thể, tôi đã thực hiện:
- **Smoke test từng sprint**: sau khi Sprint 1 (index.py) hoàn thành, tôi chạy `list_chunks()` và `inspect_metadata_coverage()` để xác nhận 5 tài liệu đều có metadata `source`, `section`, `effective_date` — phát hiện ra một lần ChromaDB collection bị xóa do merge code sai, dẫn đến `PIPELINE_ERROR: Collection [rag_lab] does not exist`.
- **Environment validation trên Windows**: kiểm tra `pip install -r requirements.txt`, ép UTF-8 cho terminal PowerShell (`chcp 65001`), và xác nhận `.env` load đúng biến `OPENAI_API_KEY`. Tôi phát hiện lỗi `Authentication 401` trên máy của Trường do file `.env.local` ghi đè `.env` nhưng `load_dotenv()` không tìm thấy.
- **Regression test giữa baseline và variant**: tôi chạy lần lượt `python eval.py` với `BASELINE_CONFIG` và `VARIANT_CONFIG`, so sánh output `scorecard_baseline.md` với `scorecard_variant.md`. Tôi ghi lại delta từng metric vào Google Sheet để nhóm theo dõi tiến độ A/B real-time trong buổi lab.
- **Grading run verification**: tôi chạy thử 10 câu từ `test_questions.json` và sau đó kiểm tra `logs/grading_run.json` để đảm bảo format JSON hợp lệ và timestamp nằm trong khung giờ cho phép.

Phần việc của tôi đóng vai trò "lớp bảo vệ" cuối cùng trước khi deliverables được nộp.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Tôi hiểu rõ hơn về **sự khác biệt giữa "code chạy" và "pipeline chạy đúng"**. Trước lab này, tôi nghĩ kiểm thử chỉ là kiểm tra output có ra hay không. Thực tế cho thấy pipeline có thể chạy hết 10 câu hỏi nhưng scorecard vẫn sai do LLM judge trả về scale không đồng nhất (Completeness bị `100` hoặc `0` thay vì 1–5). Điều này dạy tôi cần kiểm tra không chỉ "có file output" mà còn phải **validate range của từng metric**.

Tôi cũng hiểu rõ hơn về **tầm quan trọng của reproducible environment**. Cùng một repo, máy của Ngọc chạy được nhưng máy của Trường bị `UnicodeDecodeError` khi cài dependencies. Đó là do encoding terminal khác nhau. Từ đó tôi lập checklist môi trường gồm 4 bước: Python version, `chcp 65001`, `.env` placement, và `python index.py` trước khi chạy `eval.py`.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất là debug **"false abstain"** — những câu mà retriever đã lấy đúng context nhưng LLM vẫn trả lờ "Không đủ dữ liệu". Cụ thể ở q10 (VIP refund), context có đề cập đến chính sách hoàn tiền chung, nhưng model lại abstain vì không thấy từ "VIP". Tôi mất nhiều thờ gian để xác định đây không phải lỗi retrieval (Context Recall = 5/5) mà là lỗi **generation threshold quá nhạy cảm**.

Điều ngạc nhiên thứ hai là **tốc độ pipeline biến động rất lớn**: câu q01 mất 8.5 giây, câu q10 chỉ mất 1.9 giây. Nguyên nhân không phải ở LLM latency mà ở `retrieve_sparse()` — mỗi lần gọi lại rebuild BM25 index từ đầu. Tôi phát hiện điều này khi theo dõi log thờ gian từng câu, giúp Minh xác nhận bug cần fix trong variant.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** *"Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"* (id: q10)

**Phân tích:**

- **Baseline (dense):** Faithfulness = 1/5, Completeness = 1/5. Pipeline trả lờ "Không đủ dữ liệu". Tuy nhiên, `expected_sources` chỉ rõ `policy/refund-v4.pdf` là nguồn đúng, và Context Recall = 5/5 chứng tỏ retriever **đã lấy đúng** tài liệu này. Vấn đề là LLM không nhận ra rằng "không có quy trình đặc biệt" chính là câu trả lờ.

- **Lỗi nằm ở đâu:** Theo góc nhìn end-to-end testing, lỗi thuộc về **prompt design — generation layer**. Prompt quá cứng nhắc ở quy tắc "Nếu không đủ thông tin → abstain" mà không hướng dẫn LLM rằng *"nếu tài liệu có đề cập chủ đề liên quan nhưng không có ngoại lệ đặc biệt, hãy nêu quy trình chung"*. Đây là một test case điển hình cho **negative question** — câu hỏi về sự vắng mặt của một quy định.

- **Variant (hybrid):** Không cải thiện (F=1, C=1). Vì lỗi nằm ở generation, việc thay đổi retrieval mode từ dense sang hybrid không giúp được. Điều này là bằng chứng cho quy tắc A/B của nhóm: *chỉ đổi một biến retrieval* thì không fix được lỗi generation.

- **Đề xuất fix cụ thể:** Thêm một dòng vào grounded prompt: *"Nếu tài liệu đề cập đến chủ đề của câu hỏi nhưng không có ngoại lệ hoặc quy định đặc biệt, hãy trả lờ theo quy trình chung được mô tả."* Fix này không tốn chi phí tính toán và kỳ vọng sẽ nâng Completeness của q10 từ 1 lên 4–5.

---

## 5. Nếu có thêm thờ gian, tôi sẽ làm gì?

Tôi sẽ xây dựng **automated test suite** gồm 3 loại test case: (1) câu có expected source rõ ràng (như q01), (2) câu thiếu context bắt buộc abstain (như q09), và (3) câu negative question như q10. Mỗi loại sẽ có assertion riêng — ví dụ q10 không được trả về "Không đủ dữ liệu" nếu `context_recall = 5`. Tôi chọn cải tiến này vì kết quả test hiện tại cho thấy nhóm chỉ kiểm tra type (1) kỹ lưỡng, trong khi type (3) là kẽ hở lớn nhất của pipeline trong môi trường doanh nghiệp thực tế.

---
