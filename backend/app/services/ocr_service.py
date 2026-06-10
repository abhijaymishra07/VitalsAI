from io import BytesIO

from PIL import Image
import pytesseract
from pypdf import PdfReader

from app.core.config import settings

MAX_PDF_PAGES = 25
MAX_OCR_PAGES = 10
MAX_TEXT_CHARS = 80_000
MAX_IMAGE_WIDTH = 1800
MIN_TEXT_CHARS_FOR_PDF = 80


class OCRService:
    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= MAX_TEXT_CHARS:
            return text
        return text[:MAX_TEXT_CHARS]

    @staticmethod
    def tesseract_available() -> bool:
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def _ocr_image(image: Image.Image) -> str:
        if not OCRService.tesseract_available():
            return ""
        return pytesseract.image_to_string(image, lang=settings.ocr_language, config="--psm 6")

    @staticmethod
    def _extract_pdf_with_pymupdf(content: bytes) -> str:
        try:
            import fitz
        except ImportError:
            return ""

        parts: list[str] = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for i, page in enumerate(doc):
                if i >= MAX_PDF_PAGES:
                    break
                parts.append(page.get_text("text") or "")
        except Exception:
            return ""
        return "\n".join(parts).strip()

    @staticmethod
    def _extract_pdf_with_pypdf(content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = []
            for i, page in enumerate(reader.pages):
                if i >= MAX_PDF_PAGES:
                    break
                pages.append(page.extract_text() or "")
            return "\n".join(pages).strip()
        except Exception:
            return ""

    @staticmethod
    def _ocr_pdf_pages(content: bytes) -> str:
        if not OCRService.tesseract_available():
            return ""

        try:
            import fitz
        except ImportError:
            return ""

        parts: list[str] = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for i, page in enumerate(doc):
                if i >= MAX_OCR_PAGES:
                    break
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = OCRService._ocr_image(image)
                if text.strip():
                    parts.append(text)
        except Exception:
            return ""
        return "\n".join(parts).strip()

    @staticmethod
    def extract_pdf(content: bytes) -> tuple[str, str]:
        text = OCRService._extract_pdf_with_pymupdf(content)
        if len(text) >= MIN_TEXT_CHARS_FOR_PDF:
            return OCRService._truncate(text), "pdf_text"

        fallback = OCRService._extract_pdf_with_pypdf(content)
        if len(fallback) > len(text):
            text = fallback
        if len(text) >= MIN_TEXT_CHARS_FOR_PDF:
            return OCRService._truncate(text), "pdf_text"

        ocr_text = OCRService._ocr_pdf_pages(content)
        if len(ocr_text) > len(text):
            text = ocr_text
            if text.strip():
                return OCRService._truncate(text), "pdf_ocr"

        if text.strip():
            return OCRService._truncate(text), "pdf_sparse"

        if OCRService.tesseract_available():
            return "", "pdf_unreadable"
        return "", "pdf_needs_tesseract"

    @staticmethod
    async def extract_text(file) -> tuple[str, str]:
        content = await file.read()
        return OCRService.extract_text_from_bytes(file.filename or "", content)

    @staticmethod
    def extract_text_from_bytes(filename: str, content: bytes) -> tuple[str, str]:
        file_name = filename or "upload.bin"

        if file_name.lower().endswith(".txt"):
            return OCRService._truncate(content.decode("utf-8", errors="ignore")), "txt"

        if file_name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            image = Image.open(BytesIO(content))
            if image.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / image.width
                image = image.resize((MAX_IMAGE_WIDTH, int(image.height * ratio)))
            if not OCRService.tesseract_available():
                return "", "image_needs_tesseract"
            text = OCRService._ocr_image(image)
            return OCRService._truncate(text), "image_ocr"

        if file_name.lower().endswith(".pdf"):
            return OCRService.extract_pdf(content)

        return OCRService._truncate(content.decode("utf-8", errors="ignore")), "binary_guess"
