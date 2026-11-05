"""
تحليل الملفات المرفوعة (PDF, DOCX, TXT)
يستخلص النص من برنامج التخصص
"""
import io


def parse_uploaded_file(file_bytes: bytes, filename: str) -> str:
    """تحليل الملف المرفوع واستخراج النص الكامل"""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext == "pdf":
        return _parse_pdf(file_bytes)
    elif ext == "docx":
        return _parse_docx(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"صيغة الملف غير مدعومة: .{ext} (يدعم PDF و DOCX و TXT)")


def _parse_pdf(file_bytes: bytes) -> str:
    """استخراج النص من PDF (أول 20 صفحة كحد أقصى)"""
    import pdfplumber
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages[:20]):
            page_text = page.extract_text() or ""
            text += page_text + "\n"
            if i >= 19:
                text += "\n... (الوثيقة أطول، تم استخراج أول 20 صفحة)"
                break
    return text


def _parse_docx(file_bytes: bytes) -> str:
    """استخراج النص من DOCX"""
    import docx
    doc = docx.Document(io.BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs])
    return text
