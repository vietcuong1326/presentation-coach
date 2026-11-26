from typing import List, Dict, Any, Union
from pathlib import Path
import io
import fitz  # PyMuPDF
from app.core.errors import AppException


def extract_text_from_pdf(file_source: Union[str, Path, bytes]) -> List[Dict[str, Any]]:
    """
    Extracts text per page from a PDF presentation file.
    Returns:
        [
            {"page_number": 1, "text": "Slide 1 title and content"},
            {"page_number": 2, "text": "Slide 2 content"},
            ...
        ]
    """
    try:
        if isinstance(file_source, bytes):
            doc = fitz.open(stream=file_source, filetype="pdf")
        else:
            doc = fitz.open(str(file_source))

        pages_content = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            pages_content.append({
                "page_number": page_idx + 1,
                "text": text,
            })

        doc.close()
        return pages_content
    except Exception as e:
        raise AppException(
            code="PDF_EXTRACTION_ERROR",
            message=f"Failed to extract text from PDF slide file: {str(e)}",
            status_code=400,
        )

