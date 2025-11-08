
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import pypdf
import pytesseract
from PIL import Image
import io
import docx

class DocumentProcessingService:
    """
    A service for preprocessing various document types (PDF, images, DOCX).
    Handles OCR, text extraction, and basic cleaning.
    """

    def __init__(self):
        # Configure pytesseract path if necessary
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass

    async def extract_text_from_pdf(self, file_path: str | Path) -> str:
        """Extracts text from a PDF document, performing OCR if necessary."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        text_content = []
        try:
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                else:
                    # If no text is extracted, try OCR
                    images = page.images
                    for img in images:
                        image_bytes = img.data
                        if image_bytes:
                            try:
                                pil_image = Image.open(io.BytesIO(image_bytes))
                                ocr_text = pytesseract.image_to_string(pil_image)
                                if ocr_text:
                                    text_content.append(ocr_text)
                            except Exception as ocr_e:
                                print(f"OCR failed for an image in PDF: {ocr_e}")
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF {file_path}: {e}")

        return "\n".join(text_content).strip()

    async def extract_text_from_image(self, file_path: str | Path) -> str:
        """Extracts text from an image file using OCR."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from image {file_path}: {e}")

    async def extract_text_from_docx(self, file_path: str | Path) -> str:
        """Extracts text from a DOCX document."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        try:
            document = docx.Document(file_path)
            full_text = []
            for para in document.paragraphs:
                full_text.append(para.text)
            return "\n".join(full_text).strip()
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from DOCX {file_path}: {e}")

    async def preprocess_document(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Determines document type and extracts text, then performs basic cleaning.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        file_extension = file_path.suffix.lower()
        extracted_text = ""

        if file_extension == ".pdf":
            extracted_text = await self.extract_text_from_pdf(file_path)
        elif file_extension in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
            extracted_text = await self.extract_text_from_image(file_path)
        elif file_extension == ".docx":
            extracted_text = await self.extract_text_from_docx(file_path)
        else:
            # For other text-based files, just read content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            except Exception as e:
                raise RuntimeError(f"Unsupported file type or failed to read {file_path}: {e}")

        # Basic text cleaning
        cleaned_text = self._clean_text(extracted_text)

        return {
            "original_file_path": str(file_path),
            "extracted_text": cleaned_text,
            "file_extension": file_extension,
            "metadata": {} # Placeholder for more advanced metadata extraction
        }

    def _clean_text(self, text: str) -> str:
        """Performs basic text cleaning (e.g., removing excessive whitespace)."""
        # Remove multiple spaces, newlines, tabs
        text = " ".join(text.split())
        return text
