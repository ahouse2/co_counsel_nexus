from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image, ImageChops, ImageEnhance
import numpy as np
from pypdf import PdfReader
import httpx
import json

from backend.app.services.web_scraper_service import WebScraperService
from backend.app.services.blockchain_service import BlockchainService
from backend.app.config import get_settings
from backend.app.services.llm_service import get_llm_service # Assuming LLM service exists

class PDFAuthenticatorTool:
    """
    A tool to perform forensic analysis on PDF documents to detect tampering.
    """
    def __init__(self):
        settings = get_settings()
        self.verify_pdf_endpoint = settings.verify_pdf_endpoint
        self.verify_pdf_api_key = settings.verify_pdf_api_key

    async def analyze_document(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Performs a full authenticity analysis on a PDF file.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        report = {
            "file_path": str(file_path),
            "sha256_hash": self._get_file_hash(file_path),
            "metadata_analysis": self._analyze_metadata(file_path),
            "structure_analysis": self._analyze_structure(file_path),
            "verify_pdf_check": await self._verify_pdf_api_check(file_path)
        }
        return report

    def _get_file_hash(self, filepath: Path) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def _analyze_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extracts and analyzes metadata for signs of tampering."""
        try:
            reader = PdfReader(file_path)
            metadata = reader.metadata
            analysis = {
                "raw_metadata": {key: metadata[key] for key in metadata},
                "warnings": []
            }
            if metadata.get('/Author') and metadata.get('/Creator'):
                if metadata.get('/Author') != metadata.get('/Creator'):
                    analysis["warnings"].append("Author and Creator metadata do not match.")
            
            if metadata.get('/CreationDate') and metadata.get('/ModDate'):
                creation_date_str = str(metadata.get('/CreationDate'))
                mod_date_str = str(metadata.get('/ModDate'))
                # Simple check: if modified date is much later than creation date, might be suspicious
                # More robust date parsing and comparison would be needed for production
                if mod_date_str > creation_date_str:
                     analysis["warnings"].append(f"Modification date ({mod_date_str}) is after creation date ({creation_date_str}).")

            # Check for suspicious software used for creation
            creator = metadata.get('/Creator', '').lower()
            if "photoshop" in creator or "acrobat pro" in creator:
                analysis["warnings"].append(f"Document created/modified by potentially manipulative software: {creator}.")

            return analysis
        except Exception as e:
            return {"error": f"Failed to read PDF metadata: {e}"}

    def _analyze_structure(self, file_path: Path) -> Dict[str, Any]:
        """Analyzes the internal structure of the PDF for anomalies."""
        analysis = {"warnings": []}
        try:
            reader = PdfReader(file_path)
            if reader.trailer.get("/Prev"):
                analysis["warnings"].append("Multiple versions (incremental updates) found. This can be legitimate but may also indicate modification after initial creation.")
            
            # Check for unusual object streams or embedded files
            # Advanced structural checks would involve parsing the PDF stream for anomalies
            count_xrefs = len(reader.xrefs)
            if count_xrefs > 1:
                analysis["warnings"].append(f"Multiple XRef sections detected ({count_xrefs}), potentially indicating incremental saves/modifications.")

            return analysis
        except Exception as e:
            return {"error": f"Failed to analyze PDF structure: {e}"}

    async def _verify_pdf_api_check(self, file_path: Path) -> Dict[str, Any]:
        """
        Integrates with an external VerifyPDF API for authenticity checks.
        """
        if not self.verify_pdf_endpoint or not self.verify_pdf_api_key:
            return {"status": "skipped", "reason": "VerifyPDF API credentials not configured."}

        async with httpx.AsyncClient() as client:
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (file_path.name, f.read(), "application/pdf")}
                    headers = {"x-api-key": self.verify_pdf_api_key}
                    response = await client.post(self.verify_pdf_endpoint, files=files, headers=headers, timeout=60)
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"status": "error", "reason": f"VerifyPDF API failed with status {e.response.status_code}", "details": e.response.text}
            except httpx.RequestError as e:
                return {"status": "error", "reason": f"VerifyPDF API request error: {e}"}
            except Exception as e:
                return {"status": "error", "reason": f"An unexpected error during VerifyPDF API call: {e}"}


class ImageAuthenticatorTool:
    """
    A tool to perform forensic analysis on images to detect tampering.
    """
    def perform_ela(self, file_path: str | Path, quality: int = 90, scale: int = 15) -> Path:
        """
        Performs Error Level Analysis (ELA) on an image.
        ELA works by re-saving the image at a specific quality level and
        finding the difference between the original and the re-saved version.
        Manipulated areas will often have a higher error level.

        :param file_path: Path to the image to analyze.
        :param quality: The JPEG quality level to re-save at (1-100).
        :param scale: The brightness enhancement scale for the ELA result.
        :return: Path to the saved ELA image.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        original = Image.open(file_path).convert('RGB')
        
        # Re-save the image to a temporary in-memory file
        from io import BytesIO
        temp_buffer = BytesIO()
        original.save(temp_buffer, 'JPEG', quality=quality)
        temp_buffer.seek(0)
        
        resaved = Image.open(temp_buffer)

        # Find the difference between the original and the re-saved image
        ela_image = ImageChops.difference(original, resaved)
        
        # Enhance the ELA image to make differences more visible
        enhancer = ImageEnhance.Brightness(ela_image)
        ela_image = enhancer.enhance(scale)

        # Save the ELA result
        ela_path = file_path.parent / f"{file_path.stem}_ela.jpg"
        ela_image.save(ela_path, 'JPEG')
        
        return ela_path

    def analyze_exif(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Extracts and returns EXIF metadata from an image.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            image = Image.open(file_path)
            exif_data = image.getexif()
            
            if not exif_data:
                return {"message": "No EXIF metadata found."}

            # Decode EXIF tags
            from PIL.ExifTags import TAGS
            decoded_exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                # Bytes values are often unreadable, decode if possible
                if isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except UnicodeDecodeError:
                        value = value.hex()
                decoded_exif[tag] = value
            
            return decoded_exif
        except Exception as e:
            return {"error": f"Failed to read EXIF data: {e}"}

class CryptoTrackerTool:
    """
    A tool to find and perform initial analysis on cryptocurrency wallets in text.
    """
    def __init__(self):
        self.blockchain_service = BlockchainService()

    async def find_wallets_in_text(self, text: str) -> Dict[str, list]:
        """
        Finds potential cryptocurrency wallet addresses in a block of text.
        """
        import re
        
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        btc_pattern = r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})\b'

        eth_wallets = re.findall(eth_pattern, text)
        btc_wallets = re.findall(btc_pattern, text)

        return {
            "ethereum_wallets": eth_wallets,
            "bitcoin_wallets": btc_wallets,
        }

    async def get_wallet_info(self, address: str, blockchain: str) -> Dict[str, Any]:
        """
        Retrieves transaction history and balance for a given wallet address.
        """
        if blockchain.lower() == "ethereum":
            transactions = await self.blockchain_service.get_ethereum_transactions(address)
            balance_info = await self.blockchain_service.get_address_balance(address, "ethereum")
            return {"transactions": transactions, "balance": balance_info}
        elif blockchain.lower() == "bitcoin":
            transactions = await self.blockchain_service.get_bitcoin_transactions(address)
            balance_info = await self.blockchain_service.get_address_balance(address, "bitcoin")
            return {"transactions": transactions, "balance": balance_info}
        else:
            return {"error": "Unsupported blockchain for wallet info."}


class FinancialAnalysisTool:
    """
    A tool for performing forensic analysis on financial data.
    """
    def __init__(self):
        self.llm_service = get_llm_service()

    async def analyze_csv_data(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Performs statistical analysis on a CSV file, including Benford's Law.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        import pandas as pd

        df = pd.read_csv(file_path)
        
        results = {}
        
        # Descriptive Statistics
        results['descriptive_stats'] = df.describe().to_dict()

        # Benford's Law analysis on the first numerical column
        numeric_cols = df.select_dtypes(include=np.number).columns
        if not numeric_cols.empty:
            first_col = numeric_cols[0]
            # Drop zeros and non-positive values for Benford's
            s = df[first_col][df[first_col].apply(lambda x: isinstance(x, (int, float)) and x > 0)]
            if not s.empty:
                first_digits = s.astype(str).str[0].astype(int)
                benford_dist = first_digits.value_counts(normalize=True).sort_index()
                results['benford_distribution'] = benford_dist.to_dict()

        # Anomaly detection using LLM
        if results:
            prompt = f"Analyze the following financial data results for any anomalies or red flags:\n{json.dumps(results, indent=2)}\n\nProvide a detailed analysis of any suspicious patterns or deviations."
            anomaly_analysis = await self.llm_service.generate_text(prompt)
            results['llm_anomaly_analysis'] = anomaly_analysis

        return results