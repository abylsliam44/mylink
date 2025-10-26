from typing import Any, Dict
import base64
from io import BytesIO
try:
    from pdf2image import convert_from_bytes  # type: ignore
    import pytesseract  # type: ignore
    _OCR_AVAILABLE = True
except Exception:
    convert_from_bytes = None  # type: ignore
    pytesseract = None  # type: ignore
    _OCR_AVAILABLE = False
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF using OCR Tesseract only."""
    text = ""
    if not _OCR_AVAILABLE:
        return ""
    try:
        # Convert PDF pages to images and use OCR
        images = convert_from_bytes(pdf_bytes, fmt='png', dpi=300)  # type: ignore
        ocr_text_parts = []
        for img in images:  # type: ignore
            try:
                # Use Tesseract OCR with Russian and English languages
                ocr_text = pytesseract.image_to_string(img, lang='eng+rus')  # type: ignore
                if ocr_text.strip():
                    ocr_text_parts.append(ocr_text.strip())
            except Exception as e:
                print(f"OCR error for page: {e}")
                pass
        text = "\n".join(ocr_text_parts).strip()
    except Exception as e:
        print(f"PDF to image conversion error: {e}")
        pass
    return text


def run_mismatch_detector(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Optional: cv_pdf_b64 input → enrich cv_text
    try:
        b64 = payload.get("cv_pdf_b64")
        if isinstance(b64, str) and b64.strip():
            try:
                pdf_bytes = base64.b64decode(b64.strip(), validate=True)
                pdf_text = _extract_text_from_pdf_bytes(pdf_bytes)
                if pdf_text:
                    # Prepend for context and keep original cv_text
                    orig = payload.get("cv_text") or ""
                    payload = {**payload, "cv_text": f"{orig}\n\n{pdf_text}" if orig else pdf_text}
            except Exception:
                pass
    except Exception:
        pass

    agent = MismatchDetectorAgent()
    return agent.run(payload)
