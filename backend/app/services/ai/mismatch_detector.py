from typing import Any, Dict
import base64
from io import BytesIO
from pypdf import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract_text
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Best-effort text extraction: PyPDF first, then pdfminer fallback."""
    text = ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages).strip()
    except Exception:
        pass
    if len(text) < 30:
        try:
            text = (pdfminer_extract_text(BytesIO(pdf_bytes)) or "").strip()
        except Exception:
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
