"""Document ingestion core. Extracts text; never executes document contents."""
from __future__ import annotations
from pathlib import Path
import csv
import io

MAX_TEXT_CHARS = 120_000


def extract_document(filename: str, raw: bytes) -> dict:
    suffix = Path(filename or "upload").suffix.lower()
    text = ""
    if suffix in {".txt", ".md", ".json", ".py", ".kt", ".java", ".js", ".ts", ".html", ".xml", ".yaml", ".yml"}:
        text = raw.decode("utf-8-sig", errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            text += "\n" + "\n".join(" | ".join(c.text for c in row.cells) for row in table.rows)
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"Лист: {ws.title}")
            for row in ws.iter_rows(values_only=True):
                values = ["" if v is None else str(v) for v in row]
                if any(values): parts.append(" | ".join(values))
        text = "\n".join(parts)
    elif suffix == ".csv":
        decoded = raw.decode("utf-8-sig", errors="replace")
        text = "\n".join(" | ".join(row) for row in csv.reader(io.StringIO(decoded)))
    else:
        raise ValueError(f"Формат {suffix or 'без расширения'} пока не поддерживается. Поддерживаются PDF, DOCX, TXT, MD, CSV, XLSX и исходный код.")
    text = text[:MAX_TEXT_CHARS]
    return {"filename": filename, "text": text, "characters": len(text), "truncated": len(text) >= MAX_TEXT_CHARS}
