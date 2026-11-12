"""
PDF Module Pipeline for Quest Study.
Implements Section 11 of quest-study-guide-update.pdf.
Uses PyMuPDF for parsing, pytesseract for OCR on low-text pages (<50 chars),
and keyword chunk selection for grounding without requiring pgvector or embeddings.
"""
import io
import logging
import re
from pathlib import Path
from django.conf import settings

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF
from PIL import Image
import pytesseract

from core.constants import (
    CHUNK_TOKENS,
    GROUNDING_TOKENS,
    OCR_MIN_CHARS_PER_PAGE,
)

logger = logging.getLogger(__name__)


def _run_ocr_on_page(page) -> str:
    """
    Renders a PyMuPDF page to an image and runs pytesseract with lang="ind+eng".
    """
    tess_cmd = getattr(settings, "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    try:
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        # Pass lang="ind+eng" as specified in Section 0.3 and 11
        try:
            return pytesseract.image_to_string(image, lang="ind+eng")
        except Exception:
            try:
                return pytesseract.image_to_string(image, lang="eng")
            except Exception:
                return pytesseract.image_to_string(image)
    except Exception as e:
        logger.warning(f"OCR pass failed on page: {e}")
        return ""


def process_pdf_file(file_obj_or_path) -> dict:
    """
    Runs Section 11 pipeline steps 2–5:
    2. Parser pass: extract text layer per page with PyMuPDF.
    3. Decide per page: pages with stripped text < OCR_MIN_CHARS_PER_PAGE go to OCR.
    4. OCR pass on flagged pages only, recording 1-based page numbers in ocr_pages.
    5. Assemble extracted_text in page order.
    Returns:
      {
        "extracted_text": str,
        "page_count": int,
        "ocr_pages": list[int],
      }
    """
    if hasattr(file_obj_or_path, "read"):
        content = file_obj_or_path.read()
        doc = fitz.open(stream=content, filetype="pdf")
    else:
        doc = fitz.open(str(file_obj_or_path))

    page_count = len(doc)
    page_texts = []
    ocr_pages = []

    for page_idx in range(page_count):
        page = doc[page_idx]
        page_num = page_idx + 1

        parser_text = (page.get_text() or "").strip()

        if len(parser_text) < OCR_MIN_CHARS_PER_PAGE:
            ocr_pages.append(page_num)
            ocr_result = _run_ocr_on_page(page).strip()
            # If OCR yielded text, prefer it; otherwise keep parser text
            page_text = ocr_result if ocr_result else parser_text
        else:
            page_text = parser_text

        page_texts.append(page_text)

    assembled_text = "\n\n".join(page_texts).strip()

    return {
        "extracted_text": assembled_text,
        "page_count": page_count,
        "ocr_pages": ocr_pages,
    }


def chunk_text(text: str, chunk_tokens: int = CHUNK_TOKENS) -> list[str]:
    """
    Chunks text into blocks of ~chunk_tokens tokens (~4 characters per token).
    Preserves paragraph boundaries where possible.
    """
    if not text:
        return []

    char_limit = chunk_tokens * 4
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        p_len = len(p_clean)

        if current_len + p_len > char_limit and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        current_chunk.append(p_clean)
        current_len += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def select_grounded_excerpt(
    text: str,
    topic: str = "",
    min_tokens: int = GROUNDING_TOKENS[0],
    max_tokens: int = GROUNDING_TOKENS[1],
) -> str:
    """
    Section 11 steps 6–8:
    6. Chunk text into ~CHUNK_TOKENS (~500) tokens.
    7. Select chunks relevant to topic by keyword matching.
    8. Build grounded excerpt between min_tokens (2000) and max_tokens (4000).
    """
    if not text:
        return ""

    chunks = chunk_text(text, CHUNK_TOKENS)
    if not chunks:
        return ""

    # Keyword terms from topic
    keywords = [
        re.escape(w.lower().strip())
        for w in re.split(r"\W+", topic)
        if len(w.strip()) >= 3
    ]

    def score(chunk):
        c_lower = chunk.lower()
        if not keywords:
            return 0
        return sum(len(re.findall(kw, c_lower)) for kw in keywords)

    scored_chunks = sorted(chunks, key=score, reverse=True)

    min_chars = min_tokens * 4
    max_chars = max_tokens * 4

    selected = []
    total_chars = 0

    for chunk in scored_chunks:
        if total_chars + len(chunk) <= max_chars:
            selected.append(chunk)
            total_chars += len(chunk)
        elif not selected:
            selected.append(chunk[:max_chars])
            total_chars += max_chars
            break

    # If still below min_chars, fill with remaining chunks in order
    if total_chars < min_chars:
        for chunk in chunks:
            if chunk not in selected:
                remaining_space = max_chars - total_chars
                if remaining_space <= 0:
                    break
                if len(chunk) <= remaining_space:
                    selected.append(chunk)
                    total_chars += len(chunk)
                else:
                    selected.append(chunk[:remaining_space])
                    total_chars += remaining_space
                    break

    return "\n\n---\n\n".join(selected)


def get_batch_text_slice(
    text: str,
    batch_index: int = 1,
    total_batches: int = 5,
    topic: str = "",
    min_chars: int = 1200,
    max_chars: int = 3500,
) -> str:
    """
    Slices the full module text across batches so that each batch (Batch 1, Batch 2, ..., Batch N)
    is grounded in a different section of the module rather than seeing the same introductory
    excerpt over and over.
    - Batch 1: Opening section / foundational concepts (Pages/chunks at the start).
    - Batches 2..(N-1): Sequential sections covering formulas, properties, and worked examples.
    - Batch N: Final sections / applications / comprehensive review.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return ""

    chunks = chunk_text(clean_text, chunk_tokens=CHUNK_TOKENS)
    if not chunks:
        return clean_text[:max_chars]

    total_chunks = len(chunks)
    if total_chunks <= 1:
        return chunks[0][:max_chars]

    total_b = max(1, total_batches)
    batch_idx_0 = max(0, min(batch_index - 1, total_b - 1))

    # Calculate starting chunk index proportionally across the document
    step = (total_chunks - 1) / max(1, total_b - 1) if total_b > 1 else 0
    center_idx = round(batch_idx_0 * step)

    # Pick 2-3 chunks around center_idx
    start_idx = max(0, min(center_idx, total_chunks - 1))
    end_idx = min(start_idx + 2, total_chunks)

    selected_chunks = chunks[start_idx:end_idx]
    slice_text = "\n\n---\n\n".join(selected_chunks)

    if len(slice_text) < min_chars and total_chunks > len(selected_chunks):
        if end_idx < total_chunks:
            selected_chunks.append(chunks[end_idx])
        elif start_idx > 0:
            selected_chunks.insert(0, chunks[start_idx - 1])
        slice_text = "\n\n---\n\n".join(selected_chunks)

    return slice_text[:max_chars].strip()



def draft_quest_split_from_module(module, max_splits: int = 4) -> list[dict]:
    """
    Section 9 Step 4: From a module, draft a proposed quest split —
    e.g. one quest per sub-topic/section in the module — as drafts for teacher approval.
    """
    text = (module.extracted_text or "").strip()
    if not text:
        return []

    lines = text.split("\n")
    headers = []
    for line in lines:
        line_s = line.strip()
        # Look for chapter/section headings or short title lines
        if 5 <= len(line_s) <= 60 and not line_s.endswith("."):
            if any(line_s.lower().startswith(p) for p in ("bab ", "chapter ", "bagian ", "unit ", "topik ", "section ")):
                headers.append(line_s)
            elif re.match(r"^[0-9]+(\.[0-9]+)*\s+[A-Z]", line_s):
                headers.append(line_s)

    if len(headers) < 2:
        # Fallback to topic chunks
        base_topic = module.topic or module.subject or "Module Study"
        return [
            {
                "title": f"{base_topic}: Core Concepts",
                "subject": module.subject,
                "description": f"Draft quest exploring fundamental concepts from {base_topic}.",
            },
            {
                "title": f"{base_topic}: Practice & Analysis",
                "subject": module.subject,
                "description": f"Draft quest applying principles and problem solving for {base_topic}.",
            },
        ]

    chosen_headers = headers[:max_splits]
    return [
        {
            "title": h,
            "subject": module.subject,
            "description": f"Draft quest covering '{h}' from module {module.topic or module.subject}.",
        }
        for h in chosen_headers
    ]
