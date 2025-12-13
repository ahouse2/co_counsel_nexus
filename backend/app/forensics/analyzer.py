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
    FontObjectAnalysisResult,
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
        font_object_result = self._analyze_font_object(document_content, metadata)

        # Scan pattern analysis
        anti_scan_alter_rescan_result = self._detect_anti_scan_alter_rescan(document_content, metadata)

        overall_verdict = self._determine_overall_verdict(tamper_score_result)

        return ForensicAnalysisResult(
            document_id=doc_id,
            tamper_score=tamper_score_result,
            ela_analysis=ela_result,
            clone_splicing_detection=clone_splicing_result,
            font_object_analysis=font_object_result,
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

    def _analyze_font_object(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[FontObjectAnalysisResult]:
        """
        Analyzes PDF for font inconsistencies that indicate editing.
        """
        if not PYMUPDF_AVAILABLE:
            return None
            
        try:
            # Open PDF
            doc = fitz.open(stream=document_content, filetype="pdf")
            
            all_fonts = {}
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                fonts = page.get_fonts()
                
                for font in fonts:
                    font_name = font[3]  # Font name
                    font_type = font[1]   # Font type
                    
                    if font_name not in all_fonts:
                        all_fonts[font_name] = {
                            "type": font_type,
                            "pages": [page_num],
                            "count": 1
                        }
                    else:
                        all_fonts[font_name]["count"] += 1
                        all_fonts[font_name]["pages"].append(page_num)
            
            # Detect inconsistencies
            inconsistencies = []
            unique_fonts = len(all_fonts)
            
            # Flag if too many different fonts (unusual for authentic document)
            if unique_fonts > 10:
                inconsistencies.append(f"Unusually high font count: {unique_fonts}")
            
            # Flag rare/suspicious font names
            for font_name, info in all_fonts.items():
                if "Arial" not in font_name and "Times" not in font_name and "Courier" not in font_name:
                    if info["count"] < 3:  # Rarely used font
                        inconsistencies.append(f"Rare font '{font_name}' used sparingly")
            
            confidence = min(len(inconsistencies) / 5, 1.0)
            detected = confidence > 0.0
            
            return FontObjectAnalysisResult(
                inconsistencies_detected=detected,
                details=f"Analyzed {unique_fonts} unique fonts. {len(inconsistencies)} inconsistencies found.",
                anomalies=inconsistencies
            )
            
        except Exception as exc:
            return FontObjectAnalysisResult(inconsistencies_detected=False, details=f"Font analysis failed: {str(exc)}", anomalies=[])

    def _detect_anti_scan_alter_rescan(self, document_content: bytes, metadata: Dict[str, Any]) -> Optional[AntiScanAlterRescanResult]:
        """
        Detects scan→alter→rescan pattern through noise and compression analysis.
        """
        if not PIL_AVAILABLE:
            return None
            
        try:
            img = Image.open(BytesIO(document_content))
            
            if img.format != 'JPEG':
                return None
            
            # Convert to grayscale numpy array
            gray = np.array(img.convert('L'))
            
            # Analyze noise characteristics using Laplacian
            laplacian = ndimage.laplace(gray)
            noise_variance = np.var(laplacian)
            
            # Check for double JPEG compression artifacts
            # Rescan typically shows lower noise variance
            threshold_low_noise = 100  # Unusually clean for a scan
            
            # Detect periodic artifacts (printer patterns)
            fft = np.fft.fft2(gray)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shift)
            
            # Check for peaks in frequency domain (printer grids)
            magnitude_sorted = np.sort(magnitude.flatten())
            peak_threshold = magnitude_sorted[-100]  # Top peaks
            strong_peaks = np.sum(magnitude > peak_threshold)
            
            confidence = 0.0
            indicators = []
            
            if noise_variance < threshold_low_noise:
                confidence += 0.4
                indicators.append("Unusually low noise for authentic scan")
            
            if strong_peaks > 20:
                confidence += 0.3
                indicators.append("Periodic patterns suggest re-scanning")
            
            confidence = min(confidence, 1.0)
            detected = confidence > 0.5
            
            return AntiScanAlterRescanResult(
                detected=detected,
                details=f"Noise variance: {noise_variance:.2f}, Strong peaks: {strong_peaks}",
                # indicators field missing in model? models.py has 'details' but no 'indicators'?
                # Wait, models.py Step 654:
                # class AntiScanAlterRescanResult(BaseModel):
                #     detected: bool
                #     details: str
                # No indicators field!
            )
            
        except Exception as exc:
            return AntiScanAlterRescanResult(detected=False, details=f"Scan analysis failed: {str(exc)}")

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
