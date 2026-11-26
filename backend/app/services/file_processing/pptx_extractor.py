from typing import List, Dict, Any, Union
from pathlib import Path
import io
from pptx import Presentation
from app.core.errors import AppException


def extract_text_from_pptx(file_source: Union[str, Path, bytes]) -> List[Dict[str, Any]]:
    """
    Extracts text per slide from a PowerPoint PPTX file.
    Returns:
        [
            {"page_number": 1, "text": "Slide 1 title and content"},
            {"page_number": 2, "text": "Slide 2 content"},
            ...
        ]
    """
    try:
        if isinstance(file_source, bytes):
            prs = Presentation(io.BytesIO(file_source))
        else:
            prs = Presentation(str(file_source))

        slides_content = []
        for slide_idx, slide in enumerate(prs.slides):
            text_runs = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            text_runs.append(text)
            
            combined_text = "\n".join(text_runs)
            slides_content.append({
                "page_number": slide_idx + 1,
                "text": combined_text,
            })

        return slides_content
    except Exception as e:
        raise AppException(
            code="PPTX_EXTRACTION_ERROR",
            message=f"Failed to extract text from PPTX slide file: {str(e)}",
            status_code=400,
        )

