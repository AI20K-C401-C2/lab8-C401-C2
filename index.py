"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.

    Args:
        raw_text: Toàn bộ nội dung file text
        filepath: Đường dẫn file để làm source mặc định

    Returns:
        Dict chứa:
          - "text": nội dung đã clean
          - "metadata": dict với source, department, effective_date, access
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    for line in lines:
        stripped_line = line.strip()

        if not header_done:
            # Nếu bắt gặp section đầu tiên, kết thúc phần đọc header
            if stripped_line.startswith("==="):
                header_done = True
                content_lines.append(line)
                continue

            # Bỏ qua các dòng trống hoặc dòng title viết hoa toàn bộ ở đầu file
            if not stripped_line or stripped_line.isupper():
                continue

            # Sử dụng regular expression để parse linh hoạt định dạng "Key: Value"
            match = re.match(r"^([^:]+):\s*(.*)$", stripped_line)
            if match:
                key, value = match.groups()
                key_lower = key.strip().lower()
                
                if "source" in key_lower:
                    metadata["source"] = value.strip()
                elif "department" in key_lower:
                    metadata["department"] = value.strip()
                elif "effective date" in key_lower:
                    metadata["effective_date"] = value.strip()
                elif "access" in key_lower:
                    metadata["access"] = value.strip()
        else:
            content_lines.append(line)

    # Nối lại vào string
    cleaned_text = "\n".join(content_lines)

    # Chuẩn hóa (Normalize) text:
    # 1. Thu gọn các khoảng trắng (spaces) thừa thành 1 dấu cách duy nhất (trừ dấu xuống dòng)
    cleaned_text = re.sub(r"[ \t]{2,}", " ", cleaned_text)
    # 2. Xóa các dòng trống dư thừa (giữ tối đa 1 dòng trống giữa 2 đoạn văn/section = 2 ký tự \n liên tiếp)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return {
        "text": cleaned_text.strip(),
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess theo chiến lược Parent-Child.
    Parent là toàn bộ nội dung của một Section.
    Child là các đoạn văn bản nhỏ (paragraph) bên trong Section đó.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    def process_section(section_name, section_text):
        content = section_text.strip()
        if not content:
            return
            
        # Tạo parent_id định danh duy nhất cho Section này (source + section_name)
        # Loại bỏ các ký tự có thể gây lỗi url hoặc file name tĩnh nếu cần, 
        # nhưng ở lab này ghép chuỗi là đủ.
        safe_section_name = section_name.replace(" ", "_").lower()
        parent_id = f"{base_metadata['source']}::{safe_section_name}"
        
        # 1. Thêm Parent Chunk vào list
        chunks.append({
            "text": content,
            "metadata": {
                **base_metadata, 
                "section": section_name,
                "chunk_type": "parent",
                "parent_id": parent_id
            }
        })
        
        # 2. Sinh các Child Chunks từ Section này và gộp vào list
        child_chunks = _split_by_size(
            content,
            base_metadata=base_metadata,
            section=section_name,
            parent_id=parent_id
        )
        chunks.extend(child_chunks)

    for part in sections:
        if re.match(r"===.*?===", part):
            process_section(current_section, current_section_text)
            # Cập nhật tên section mới (bỏ dấu ===)
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part

    # Xử lý section cuối cùng trong file
    process_section(current_section, current_section_text)

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    parent_id: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Helper: Split text dài thành các Child Chunks.
    Ưu tiên cắt theo đoạn văn (\n\n) trước, giữ cấu trúc logic.
    """
    chunks = []
    # Cắt theo ranh giới tự nhiên (đoạn văn)
    paragraphs = text.split("\n\n")
    
    current_chunk_text = ""
    
    for p in paragraphs:
        # Nếu gộp thêm paragraph này vẫn dưới giới hạn chunk_chars thì gộp
        if len(current_chunk_text) + len(p) <= chunk_chars:
            # Thêm newline vào giữa các đoạn
            current_chunk_text += (p + "\n\n")
        else:
            # Nếu current_chunk vượt quá, lưu current_chunk thành 1 block child
            if current_chunk_text.strip():
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "metadata": {
                        **base_metadata, 
                        "section": section,
                        "chunk_type": "child",
                        "parent_id": parent_id
                    }
                })
            # Khởi tạo lại chunk bằng paragraph mới
            current_chunk_text = p + "\n\n"
            
    # Xử lý đoạn cuối còn sót lại
    if current_chunk_text.strip():
        chunks.append({
            "text": current_chunk_text.strip(),
            "metadata": {
                **base_metadata, 
                "section": section,
                "chunk_type": "child",
                "parent_id": parent_id
            }
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

from openai import OpenAI

# Khởi tạo client ở cấp độ module để có thể tái sử dụng
openai_client = None

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text sử dụng mô hình OpenAI text-embedding-3-small.
    """
    global openai_client
    if openai_client is None:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB client & collection
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))

        # Gọi chunk_document
        chunks = chunk_document(doc)

        print(f"    → Tổng số {len(chunks)} chunks, đang embedding và lưu vào ChromaDB...")
        
        for i, chunk in enumerate(chunks):
            # Lấy thông tin chunk_type ra để tạo chunk_id an toàn (tránh đụng độ)
            chunk_type = chunk["metadata"].get("chunk_type", "unknown")
            chunk_id = f"{filepath.stem}_{chunk_type}_{i}"
            
            embedding = get_embedding(chunk["text"])
            
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )
            
        total_chunks += len(chunks)

    print(f"\nHoàn thành! Tổng số {total_chunks} chunks đã được nhúng và lưu vào ChromaDB.")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.

    TODO Sprint 1:
    Implement sau khi hoàn thành build_index().
    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date)
    - Chunk có bị cắt giữa điều khoản không?
    - Metadata effective_date có đúng không?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.

    Checklist Sprint 1:
    - Mọi chunk đều có source?
    - Có bao nhiêu chunk từ mỗi department?
    - Chunk nào thiếu effective_date?

    TODO: Implement sau khi build_index() hoàn thành.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTổng chunks: {len(results['metadatas'])}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thiếu effective_date: {missing_date}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    # Bước 2: Test preprocess và chunking (không cần API key)
    print("\n--- Test preprocess + chunking ---")
    for filepath in doc_files[:1]:  # Test với 1 file đầu
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Text: {chunk['text'][:150]}...")

    # Bước 3: Build index (đã implement get_embedding)
    print("\n--- Build Full Index ---")
    build_index()

    # Bước 4: Kiểm tra index
    print("\n--- Kiểm tra Index ---")
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn chỉnh!")
