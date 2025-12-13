
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import pypdf
import pytesseract
from PIL import Image
import io
import docx
import os
import math


class DocumentProcessingService:
    """
    A service for preprocessing various document types (PDF, images, DOCX).
    Handles OCR, text extraction, and basic cleaning.
    """

    def __init__(self):
        # Configure pytesseract path if necessary
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass

    def get_file_size(self, file_path: str | Path) -> int:
        """Returns the size of the file in bytes."""
        return Path(file_path).stat().st_size

    async def split_pdf(self, file_path: str | Path, max_pages: int = 50) -> List[Path]:
        """
        Splits a PDF into smaller chunks if it exceeds max_pages.
        Returns a list of paths to the chunked files (or the original if no split needed).
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            reader = pypdf.PdfReader(file_path)
            total_pages = len(reader.pages)
            
            if total_pages <= max_pages:
                return [file_path]
            
            chunks = []
            base_name = file_path.stem
            parent_dir = file_path.parent
            
            num_chunks = math.ceil(total_pages / max_pages)
            
            for i in range(num_chunks):
                start_page = i * max_pages
                end_page = min((i + 1) * max_pages, total_pages)
                
                writer = pypdf.PdfWriter()
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                chunk_filename = f"{base_name}_part_{i+1}_of_{num_chunks}.pdf"
                chunk_path = parent_dir / chunk_filename
                
                with open(chunk_path, "wb") as f:
                    writer.write(f)
                
                chunks.append(chunk_path)
                
            return chunks
            
        except Exception as e:
            print(f"Failed to split PDF {file_path}: {e}")
            # Fallback to returning original file if split fails
            return [file_path]

    async def split_text_file(self, file_path: str | Path, max_size_mb: int = 10) -> List[Path]:
        """
        Splits a text file into smaller chunks if it exceeds max_size_mb.
        Returns a list of paths to the chunked files.
        """
        file_path = Path(file_path)
        file_size = self.get_file_size(file_path)
        max_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_bytes:
            return [file_path]
            
        chunks = []
        base_name = file_path.stem
        parent_dir = file_path.parent
        suffix = file_path.suffix
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            total_chars = len(content)
            # Approximate chars per chunk (assuming 1 byte/char for simplicity in split logic, 
            # though UTF-8 varies. This is a rough split.)
            chars_per_chunk = max_bytes 
            
            num_chunks = math.ceil(total_chars / chars_per_chunk)
            
            for i in range(num_chunks):
                start = i * chars_per_chunk
                end = min((i + 1) * chars_per_chunk, total_chars)
                chunk_content = content[start:end]
                
                chunk_filename = f"{base_name}_part_{i+1}_of_{num_chunks}{suffix}"
                chunk_path = parent_dir / chunk_filename
                
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk_content)
                    
                chunks.append(chunk_path)
                
            return chunks
            
        except Exception as e:
            print(f"Failed to split text file {file_path}: {e}")
            return [file_path]


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
