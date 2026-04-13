# Báo Cáo Nhóm — Lab Day 08: RAG Pipeline

**Môn:** AI in Action (AICB-P1)  
**Nhóm:** C401-C2  
**Ngày nộp:** 2026-04-13  

---

## 1. Tổng quan bài toán

Nhóm xây dựng **trợ lý AI nội bộ** cho khối Customer Support (CS) và IT Helpdesk, có khả năng trả lờ câu hỏi về chính sách hoàn tiền, SLA ticket, quy trình cấp quyền hệ thống và FAQ. Hệ thống hoạt động theo pipeline RAG đầy đủ: **Indexing → Retrieval → Generation → Evaluation**. Yêu cầu cốt lõi là mọi câu trả lờ đều phải **grounded** (dựa trên tài liệu nội bộ được retrieve), có **citation** nguồn rõ ràng, và **abstain** đúng đắn khi không đủ dữ liệu.

---

## 2. Kiến trúc Pipeline

Pipeline được triển khai qua 4 sprint tương ứng 4 file chính:

- **`index.py` (Sprint 1)**: Tiền xử lý 5 tài liệu `.txt` → Parent-Child Chunking → Embed bằng OpenAI `text-embedding-3-small` → Lưu vào ChromaDB.
- **`rag_answer.py` (Sprint 2 + 3)**: Nhận query ngườ dùng → Dense Retrieval hoặc Hybrid Retrieval (Dense + BM25 với RRF) → Chọn top-3 chunk → Build context block với citation số `[1][2][3]` → GPT-4o-mini sinh câu trả lờ.
- **`eval.py` (Sprint 4)**: Chạy 10 test questions qua cả baseline và variant → LLM-as-Judge chấm 4 metrics (Faithfulness, Relevance, Context Recall, Completeness) → Xuất scorecard và A/B comparison.

Sơ đồ luồng dữ liệu:

```
[Raw Docs] → index.py → [ChromaDB] → rag_answer.py → [Answer + Citation]
                                          ↓
                                      eval.py → [Scorecard + A/B Delta]
```

---

## 3. Quyết định Kỹ thuật Chính

### 3.1. Chunking: Parent-Child Strategy

Thay vì cắt văn bản theo số ký tự cố định (dễ cắt giữa điều khoản), nhóm chọn **Parent-Child Chunking**:
- Mỗi **Section Heading** là Parent, giữ ngữ cảnh lớn.
- Mỗi **Paragraph** (`\n\n`) trong section là Child, được embed và retrieve.
- Giới hạn child chunk ~400 tokens (~1600 ký tự), overlap = 0 (vì cắt theo ranh giới đoạn văn tự nhiên).

Mỗi chunk được gắn **6 metadata fields**: `source`, `section`, `effective_date`, `department`, `access`, `chunk_type`. Điều này giúp Context Recall đo chính xác tài liệu nguồn và hỗ trợ citation minh bạch.

### 3.2. Retrieval: Baseline Dense → Variant Hybrid

**Baseline (Sprint 2)** sử dụng Dense Retrieval trên ChromaDB với cosine similarity. Đây là lựa chọn an toàn cho ngôn ngữ tự nhiên, nhưng lộ rõ điểm yếu ở các query chứa **keyword kỹ thuật chính xác** hoặc **alias cũ** (ví dụ: "Approval Matrix" thay vì "Access Control SOP").

**Variant (Sprint 3)** là **Hybrid Retrieval** — kết hợp Dense (60%) và BM25 (40%) qua **Reciprocal Rank Fusion (RRF, k=60)**:

```
RRF_score = 0.6 × 1/(60 + dense_rank) + 0.4 × 1/(60 + sparse_rank)
```

Lý do chọn hybrid là corpus của bài toán chứa cả hai loại ngôn ngữ:
- Ngôn ngữ tự nhiên (policy mô tả) → Dense mạnh.
- Tên riêng / mã lỗi / alias ("ERR-403-AUTH", "ticket P1", "Approval Matrix") → BM25 mạnh.

Theo **A/B Rule**, nhóm chỉ thay đổi **đúng 1 biến**: `retrieval_mode` từ `"dense"` sang `"hybrid"`, giữ nguyên `top_k_search=10`, `top_k_select=3`, `use_rerank=False`, và prompt generation.

### 3.3. Generation: Grounded Prompt + Abstain

Prompt được thiết kế với 4 quy tắc cốt lõi:
1. **GROUNDED**: Chỉ dùng thông tin trong Context.
2. **ABSTAIN**: Nếu không đủ thông tin → "Không đủ dữ liệu".
3. **CITATION**: Trích dẫn `[1]`, `[2]`, `[3]` sau mỗi ý chính.
4. **NGÔN NGỮ**: Trả lờ bằng tiếng Việt.

Model chọn `gpt-4o-mini` với `temperature=0` để đảm bảo output ổn định cho evaluation.

### 3.4. Evaluation: LLM-as-Judge + Context Recall xác định

Nhóm triển khai **4 metrics**:
- **Faithfulness** (Answer có bám context không?)
- **Answer Relevance** (Có đúng trọng tâm câu hỏi không?)
- **Context Recall** (Retriever có lấy đúng nguồn không?) — được tính bằng string match `expected_sources` thay vì LLM judge, đảm bảo ổn định.
- **Completeness** (Có đầy đủ so với expected answer không?)

---

## 4. Kết quả A/B Evaluation

### 4.1. Scorecard Tổng quát

| Metric | Baseline (Dense) | Variant (Hybrid) | Delta |
|--------|------------------|------------------|-------|
| Faithfulness | 3.80 / 5 | 3.80 / 5 | 0.00 |
| Answer Relevance | 3.80 / 5 | 3.80 / 5 | 0.00 |
| Context Recall | 5.00 / 5 | 5.00 / 5 | 0.00 |
| Completeness | 3.50 / 5 | 3.70 / 5 | **+0.20** |
| **Overall** | **4.03 / 5** | **4.08 / 5** | **+0.05** |

*(Overall = trung bình 4 metrics)*

### 4.2. Phân tích chi tiết

**Variant tốt hơn rõ rệt ở:**
- **q06 (Escalation P1)**: Completeness tăng từ **2 → 5**. Baseline bỏ sót quy trình escalate 10 phút vì chunk đúng bị đẩy xuống thấp trong top-k. Hybrid BM25 bắt chính xác từ khóa "escalate" và "10 phút", đưa chunk quan trọng vào top-3.
- **q08 (Remote work)**: Completeness tăng từ **3 → 4** (baseline) hoặc **5** (variant tùy lần chạy). BM25 ưu tiên chunk chứa "probation period" và "2 ngày/tuần".

**Variant không cải thiện ở:**
- **q07 (Approval Matrix)**: Cả hai đều fail (F=1, C=1). Context Recall = 5/5 chứng tỏ retriever đã lấy đúng file, nhưng LLM **abstain** vì không nhận ra "Approval Matrix" là tên cũ của "Access Control SOP". Đây là lỗi **generation layer**, không phải retrieval.
- **q10 (VIP refund)**: Cả hai đều abstain sai. Prompt quá cứng nhắc khi gặp câu hỏi "negative" (hỏi về sự vắng mặt của một quy định).

### 4.3. Kết luận A/B

Variant Hybrid **tốt hơn baseline** nhờ cải thiện Completeness (+0.20), đặc biệt với các query chứa keyword kỹ thuật chính xác. Faithfulness và Relevance không thay đổi vì generation prompt giữ nguyên. Nhóm quyết định **chọn Hybrid làm cấu hình chính thức** cho grading questions.

---

## 5. Phân công Công việc

| Thành viên | Vai trò | Sprint chính | Deliverable chính |
|------------|---------|-------------|-------------------|
| Phạm Việt Anh | Tech Lead | Sprint 1 | `index.py` — Parent-Child Chunking, metadata |
| Nguyễn Thùy Linh | Retrieval Owner | Sprint 2 | `retrieve_dense()`, `select_sources()` |
| Phạm Đình Trường | Generation Owner | Sprint 2 | Prompt grounded, citation, abstain logic |
| Phan Tuấn Minh | Tuning Owner | Sprint 3 | `retrieve_sparse()`, `retrieve_hybrid()`, RRF |
| Bùi Minh Ngọc | Eval + Docs Owner | Sprint 4 | `eval.py`, `architecture.md`, `tuning-log.md` |
| Phạm Việt Hoàng | Git Merge Lead | Sprint 2–3 | Resolve conflicts, fix merge artifacts |
| Lê Đức Thanh | End-to-End Test Lead | Sprint 4 | Smoke test, env validation, grading run check |

---

## 6. Kết luận và Đề xuất Cải tiến

Pipeline của nhóm đã đáp ứng đầy đủ các yêu cầu cơ bản: index đủ 5 tài liệu, retrieval có citation, generation biết abstain, và evaluation có scorecard so sánh A/B. Context Recall đạt tuyệt đối (5.00/5), chứng tỏ phần indexing và retrieval hoạt động ổn định.

Tuy nhiên, **Faithfulness và Completeness** vẫn chưa đạt tối đa do hai nhóm vấn đề chính:
1. **Alias / Negative questions**: q07 (Approval Matrix) và q10 (VIP refund) cho thấy prompt hiện tại chưa đủ linh hoạt để xử lý các câu hỏi dạng "tên cũ" hoặc "có ngoại lệ không?".
2. **Lost-in-middle effect**: dù Context Recall cao, một số chunk quan trọng bị đẩy xuống vị trí thấp trong top-k, gây thiếu sót ở generation.

Nếu có thêm thờ gian, nhóm sẽ triển khai **2 cải tiến tiếp theo**:
1. **Query Expansion**: dùng LLM để sinh alias / paraphrase trước khi retrieve (ví dụ: "Approval Matrix" → "Access Control SOP"), fix q07 mà không cần đổi corpus.
2. **Cross-Encoder Rerank**: sau Hybrid top-10, dùng cross-encoder để chấm lại relevance từng chunk và chọn top-3 chính xác nhất, giảm lost-in-middle và cải thiện Completeness cho q06.

---

*Hết báo cáo nhóm.*
