"""
Production-Grade Forensic Analysis Module

Implements advanced document forensics including:
- Error Level Analysis (ELA) for JPEG manipulation detection  
- Clone/Splicing detection using SIFT feature matching
- Font inconsistency analysis for PDF tampering
- Anti-scan-alter-rescan pattern detection
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from PIL import Image
    import numpy as np
    from scipy import ndimage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from ..forensics.models import (
    AntiScanAlterRescanResult,
    CloneSplicingResult,
    ElaResult,
    PdfStructureAnalysisResult,
    ForensicAnalysisResult,
    TamperScoreResult,
    ScreeningResult,
)


class ForensicAnalyzer:
    """Advanced forensic analysis for legal documents and images."""

    def screen_document(self, document_content: bytes, metadata: Dict[str, Any]) -> ScreeningResult:
        """
        Performs lightweight forensic screening to flag suspicious documents.
        """
        is_suspicious = False
        reasons = []
        
        # 1. Keyword Screening
        tamper_keywords = [b"tampered", b"altered", b"edited", b"photoshop", b"gimp"]
        content_lower = document_content.lower()
        for keyword in tamper_keywords:
            if keyword in content_lower:
                is_suspicious = True
                reasons.append(f"Suspicious keyword found: {keyword.decode('utf-8', errors='ignore')}")
        
        # 2. Metadata Screening (Basic)
        # e.g., check for software names in metadata if available
        # This depends on what's passed in `metadata`
        
        # 3. File Signature / Magic Bytes check (Basic)
        # (Optional implementation)

        return ScreeningResult(
            is_suspicious=is_suspicious,
            reason="; ".join(reasons) if reasons else "No obvious signs detected in screening.",
            score=0.5 if is_suspicious else 0.0 # Placeholder score
        )

    def analyze(self, document_path: Path, metadata: Dict[str, Any], doc_id: str = "") -> ForensicAnalysisResult:
        """
        Performs comprehensive forensic analysis on a document.
        """
        document_content = document_path.read_bytes()

        # Basic tamper score
        tamper_score_result = self._generate_tamper_score(document_content, metadata)

        # Advanced image forensics
        ela_result = self._perform_ela(document_content, metadata)
        clone_splicing_result = self._detect_clone_splicing(document_content, metadata)

        # PDF forensics
        pdf_structure_result = self._analyze_pdf_structure(document_content, metadata)

        # Scan pattern analysis
        anti_scan_alter_rescan_result = self._detect_anti_scan_alter_rescan(document_content, metadata)

        overall_verdict = self._determine_overall_verdict(tamper_score_result)

        return ForensicAnalysisResult(
            document_id=doc_id,
            tamper_score=tamper_score_result,
            ela_analysis=ela_result,
            clone_splicing_detection=clone_splicing_result,
            pdf_structure_analysis=pdf_structure_result,
            anti_scan_alter_rescan=anti_scan_alter_rescan_result,
            overall_verdict=overall_verdict,
        )

    def _generate_tamper_score(self, document_content: bytes, metadata: Dict[str, Any]) -> TamperScoreResult:
        """
        Performs a rudimentary tamper score generation based on simple keyword checks.
        This is a basic check and not a full forensic analysis.
        """
        score = 0.0
        flags = []
        details = "No obvious signs of tampering detected by basic checks."

        if b"tampered" in document_content.lower():
            score += 0.3
            flags.append("KEYWORD_MATCH: 'tampered'")
            details = "Keyword 'tampered' found in content."
        if b"altered" in document_content.lower():
            score += 0.2
            flags.append("KEYWORD_MATCH: 'altered'")
            details = "Keyword 'altered' found in content."

        return TamperScoreResult(score=min(score, 1.0), details=details, flags=flags)

    def _perform_ela(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[ElaResult]:
        """
        Performs Error Level Analysis (ELA) to detect JPEG manipulation.
        Areas with different compression artifacts indicate potential tampering.
        """
        if not PIL_AVAILABLE:
            return None
            
        try:
            # Load image
            img = Image.open(BytesIO(document_content))
            
            # Only works on JPEG
            if img.format != 'JPEG':
                return None
            
            # Save at quality 95% to establish baseline
            resaved = BytesIO()
            img.save(resaved, 'JPEG', quality=95)
            resaved.seek(0)
            img_resaved = Image.open(resaved)
            
            # Convert to numpy arrays
            original = np.array(img).astype(float)
            resaved_arr = np.array(img_resaved).astype(float)
            
            # Calculate absolute difference
            diff = np.abs(original - resaved_arr)
            
            # Amplify difference for visibility
            ela_image = diff * 10
            ela_image = np.clip(ela_image, 0, 255).astype(np.uint8)
            
            # Calculate statistics
            mean_error = float(np.mean(diff))
            max_error = float(np.max(diff))
            std_error = float(np.std(diff))
            
            # High variance areas indicate possible tampering
            threshold = mean_error + (2 * std_error)
            high_variance_pixels = np.sum(diff > threshold)
            total_pixels = diff.size
            tamperedPercentage = (high_variance_pixels / total_pixels) * 100
            
            confidence = min(tamperedPercentage / 10, 1.0)  # Scale to 0-1
            
            return ElaResult(
                ela_score=confidence,
                details=f"ELA detected {tamperedPercentage:.2f}% high-variance pixels. Mean error: {mean_error:.2f}, Max: {max_error:.2f}",
                ela_heatmap_url=None  # Heatmap data not supported in current model
            )
            
        except Exception as exc:
            return ElaResult(ela_score=0.0, details=f"ELA failed: {str(exc)}", ela_heatmap_url=None)

    def _detect_clone_splicing(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[CloneSplicingResult]:
        """
        Detects cloned/copy-pasted regions using SIFT keypoint matching.
        """
        if not (PIL_AVAILABLE and CV2_AVAILABLE):
            return None
            
        try:
            # Load image
            img = Image.open(BytesIO(document_content))
            img_array = np.array(img.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect SIFT keypoints
            sift = cv2.SIFT_create()
            keypoints, descriptors = sift.detectAndCompute(gray, None)
            
            if descriptors is None or len(keypoints) < 10:
                return CloneSplicingResult(detected=False, details="Insufficient keypoints detected", regions=[])
            
            # Match keypoints to find duplicates
            bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
            matches = bf.knnMatch(descriptors, descriptors, k=2)
            
            # Filter good matches (not self-matches, spatial distance check)
            good_matches = []
            
            for match_pair in matches:
                if len(match_pair) < 2:
                    continue
                m, n = match_pair
                
                # Lowe's ratio test
                if m.distance < 0.7 * n.distance:
                    # Not a self-match
                    if m.queryIdx != m.trainIdx:
                        pt1 = keypoints[m.queryIdx].pt
                        pt2 = keypoints[m.trainIdx].pt
                        
                        # Check spatial distance - if too close, it's the same region
                        dist = np.linalg.norm(np.array(pt1) - np.array(pt2))
                        if dist > 50:  # Minimum distance threshold
                            good_matches.append((pt1, pt2))
            
            confidence = min(len(good_matches) / 100, 1.0)  # Scale based on matches found
            detected = confidence > 0.1 # Low threshold for detection
            
            # Group matches into regions
            regions = []
            if len(good_matches) > 5:
                regions = [
                    f"Match between {m[0]} and {m[1]}" 
                    for m in good_matches[:10]  # Limit to top 10
                ]
            
            details = f"Found {len(good_matches)} potential clone matches"
            
            return CloneSplicingResult(
                detected=detected,
                details=details,
                regions=regions
            )
            
        except Exception as exc:
            return CloneSplicingResult(detected=False, details=f"Clone detection failed: {str(exc)}", regions=[])

    def _analyze_pdf_structure(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[PdfStructureAnalysisResult]:
        """
        Analyzes PDF for structural inconsistencies, incremental updates, and metadata anomalies.
        """
        if not PYMUPDF_AVAILABLE:
            return None
            
        try:
            # Open PDF
            doc = fitz.open(stream=document_content, filetype="pdf")
            
            anomalies = []
            metadata_inconsistencies = []
            suspicious_tags = []
            
            # 1. Incremental Update Detection (Multiple EOFs)
            # Simple check: count %%EOF in raw bytes
            eof_count = document_content.count(b'%%EOF')
            incremental_updates_detected = eof_count > 1
            if incremental_updates_detected:
                anomalies.append(f"Multiple EOF markers found ({eof_count}), indicating incremental updates/modifications.")
            
            # 2. Metadata Consistency
            pdf_metadata = doc.metadata
            creation_date = pdf_metadata.get("creationDate", "")
            mod_date = pdf_metadata.get("modDate", "")
            producer = pdf_metadata.get("producer", "")
            creator = pdf_metadata.get("creator", "")
            
            # Basic date format check (D:YYYYMMDD...)
            if creation_date and mod_date:
                # Simple string comparison works for ISO-like PDF dates if formats match
                # Ideally parse, but raw string check is often enough for obvious mismatches
                if mod_date < creation_date:
                    metadata_inconsistencies.append(f"Modification Date ({mod_date}) is earlier than Creation Date ({creation_date}).")
            
            if producer and creator and producer != creator:
                 # Not necessarily an error, but worth noting if they are vastly different tools
                 pass 
                 
            # 3. Suspicious Tags/Actions
            # Scan raw content for JS/Launch actions (simple heuristic)
            # PyMuPDF can also traverse objects, but regex on bytes is a good catch-all for hidden stuff
            suspicious_patterns = [b'/JS', b'/JavaScript', b'/AA', b'/OpenAction', b'/Launch']
            for pattern in suspicious_patterns:
                if pattern in document_content:
                    tag = pattern.decode('utf-8')
                    suspicious_tags.append(tag)
                    anomalies.append(f"Suspicious tag found: {tag}")

            # 4. Font Analysis (Existing Logic)
            all_fonts = {}
            for page_num in range(len(doc)):
                page = doc[page_num]
                fonts = page.get_fonts()
                for font in fonts:
                    font_name = font[3]
                    if font_name not in all_fonts:
                        all_fonts[font_name] = 1
                    else:
                        all_fonts[font_name] += 1
            
            unique_fonts = len(all_fonts)
            if unique_fonts > 10:
                anomalies.append(f"Unusually high font count: {unique_fonts}")
            
            confidence = min(len(anomalies) / 5, 1.0)
            detected = len(anomalies) > 0 or incremental_updates_detected
            
            return PdfStructureAnalysisResult(
                inconsistencies_detected=detected,
                details=f"Analyzed PDF Structure. {len(anomalies)} anomalies found. Incremental Updates: {incremental_updates_detected}",
                anomalies=anomalies,
                incremental_updates_detected=incremental_updates_detected,
                metadata_inconsistencies=metadata_inconsistencies,
                suspicious_tags=suspicious_tags
            )
            
        except Exception as exc:
            return PdfStructureAnalysisResult(
                inconsistencies_detected=False, 
                details=f"PDF analysis failed: {str(exc)}", 
                anomalies=[],
                incremental_updates_detected=False,
                metadata_inconsistencies=[],
                suspicious_tags=[]
            )

    def _detect_anti_scan_alter_rescan(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[AntiScanAlterRescanResult]:
        """
        Detects scan→alter→rescan pattern through noise and compression analysis.
        Implements:
        1. Moiré Pattern Detection (FFT analysis for double halftoning)
        2. Digital Silence Detection (Zero-noise regions indicating digital overlays)
        """
        if not PIL_AVAILABLE:
            return None
            
        try:
            img = Image.open(BytesIO(document_content))
            
            # Convert to grayscale numpy array
            if img.mode != 'L':
                img = img.convert('L')
            gray = np.array(img)
            
            # --- 1. Moiré Pattern Detection (Frequency Domain) ---
            # Real scans of printed documents have specific halftone frequencies.
            # Rescanning creates interference (Moiré) which shows as competing peaks in FFT.
            
            fft = np.fft.fft2(gray)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shift)
            magnitude_log = np.log(1 + magnitude)
            
            # Normalize
            magnitude_norm = (magnitude_log - np.min(magnitude_log)) / (np.max(magnitude_log) - np.min(magnitude_log))
            
            # Threshold to find peaks
            # We look for distinct high-energy points away from the center (DC component)
            h, w = magnitude_norm.shape
            center_y, center_x = h // 2, w // 2
            
            # Mask out the center (low frequencies)
            mask_radius = min(h, w) // 10
            y, x = np.ogrid[:h, :w]
            mask = (x - center_x)**2 + (y - center_y)**2 > mask_radius**2
            
            peaks = magnitude_norm * mask
            peak_count = np.sum(peaks > 0.85) # High energy peaks
            
            moire_detected = peak_count > 50 # Heuristic threshold for complex interference patterns
            
            # --- 2. Digital Silence Detection (Spatial Domain) ---
            # Real scans have sensor noise everywhere. 
            # Digital overlays (e.g. white box to hide text) have mathematically zero variance.
            
            # Split image into 16x16 blocks
            block_size = 16
            h_blocks = h // block_size
            w_blocks = w // block_size
            
            silent_blocks = 0
            total_blocks = h_blocks * w_blocks
            
            # We can use view_as_windows or simple reshaping if dimensions allow, 
            # but standard loop with stride is robust enough for now or reshaping.
            # Let's use reshaping for speed.
            
            # Crop to multiple of block_size
            h_crop = h_blocks * block_size
            w_crop = w_blocks * block_size
            gray_crop = gray[:h_crop, :w_crop]
            
            # Reshape to (n_blocks, block_size, block_size)
            # This is a bit complex with numpy reshape, let's do a simpler variance map
            
            # Calculate local variance using a sliding window or block processing
            # Faster approach:
            # 1. Square the image
            # 2. Box filter the image and the squared image
            # 3. Var = E[X^2] - (E[X])^2
            
            img_f = gray.astype(float)
            mu = ndimage.uniform_filter(img_f, size=block_size)
            sq_mu = ndimage.uniform_filter(img_f**2, size=block_size)
            variance_map = sq_mu - mu**2
            
            # "Digital Silence" is variance < 0.5 (allowing for tiny floating point errors/compression artifacts)
            # Real sensor noise usually has variance > 5-10 depending on ISO.
            silent_pixels = np.sum(variance_map < 0.5)
            silent_ratio = silent_pixels / variance_map.size
            
            digital_overlays_detected = silent_ratio > 0.01 # If more than 1% of the image is perfectly silent
            
            # --- Verdict ---
            detected = moire_detected or digital_overlays_detected
            
            details = []
            if moire_detected:
                details.append(f"Moiré patterns detected (Peak count: {peak_count})")
            if digital_overlays_detected:
                details.append(f"Digital overlays detected ({silent_ratio*100:.1f}% of area is silent)")
                
            if not details:
                details.append("No scan-alter-rescan anomalies detected")
                
            return AntiScanAlterRescanResult(
                detected=detected,
                details="; ".join(details),
                moire_detected=moire_detected,
                digital_overlays_detected=digital_overlays_detected
            )
            
        except Exception as exc:
            return AntiScanAlterRescanResult(
                detected=False, 
                details=f"Scan analysis failed: {str(exc)}",
                moire_detected=False,
                digital_overlays_detected=False
            )

    def _determine_overall_verdict(self, tamper_score: TamperScoreResult) -> str:
        if tamper_score.score >= 0.7:
            return "HIGH_TAMPER_RISK"
        elif tamper_score.score >= 0.4:
            return "MODERATE_TAMPER_RISK"
        return "LOW_TAMPER_RISK"


def get_forensic_analyzer() -> ForensicAnalyzer:
    """
    Dependency function to provide a ForensicAnalyzer instance.
    """
    return ForensicAnalyzer()
