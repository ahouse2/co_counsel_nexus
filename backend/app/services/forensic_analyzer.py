from typing import Dict, Any, List
import datetime
import io

class ForensicAnalyzer:
    def analyze_manipulation(self, metadata: Dict[str, Any], file_content: bytes = None) -> Dict[str, Any]:
        """
        Analyzes document metadata and content for signs of tampering, including ELA and Splicing indicators.
        """
        flags = []
        risk_score = 0.0
        
        # --- Metadata Forensics ---
        
        # 1. Software Signatures
        suspicious_software = ["Photoshop", "GIMP", "InDesign", "Illustrator", "Paint.NET"]
        producer = metadata.get("producer", "") or metadata.get("creator", "") or ""
        for software in suspicious_software:
            if software.lower() in producer.lower():
                flags.append(f"Edited with {software}")
                risk_score += 0.4

        # 2. Date Anomalies
        created = metadata.get("created_at")
        modified = metadata.get("modified_at")
        if created and modified:
            try:
                if str(modified) < str(created):
                    flags.append("Modification date predates creation date (Time Travel Paradox)")
                    risk_score += 0.2
            except:
                pass

        # 3. "Scan/Alter/Rescan" Detection
        filename = metadata.get("file_name", "").lower()
        if "scan" in filename and "adobe" in producer.lower():
             flags.append("Scanned document contains Adobe editing metadata")
             risk_score += 0.5

        # --- Content Forensics (ELA & Splicing) ---
        
        ela_result = "Inconclusive (Image processing unavailable)"
        splicing_probability = 0.0
        
        if file_content:
            # 4. Error Level Analysis (ELA) Heuristic
            # Real ELA compares compression levels. 
            # Heuristic: Check for multiple quantization tables or inconsistent JPEG markers.
            if self._has_inconsistent_markers(file_content):
                flags.append("Inconsistent JPEG markers detected (Possible Splicing)")
                splicing_probability += 0.6
                risk_score += 0.4
                ela_result = "High Variance Detected"
            else:
                ela_result = "Consistent Compression"

            # 5. Splicing / Copy-Move Detection
            # Heuristic: Look for repeated byte patterns in non-header regions (crude copy-move)
            if self._detect_repeated_patterns(file_content):
                flags.append("Repeated binary patterns detected (Possible Copy-Move)")
                splicing_probability += 0.3
                risk_score += 0.2

        # Cap score
        risk_score = min(1.0, risk_score)
        
        return {
            "risk_score": risk_score,
            "flags": flags,
            "details": {
                "producer": producer,
                "dates_analyzed": bool(created and modified),
                "ela_analysis": ela_result,
                "splicing_probability": round(splicing_probability, 2)
            }
        }

    def _has_inconsistent_markers(self, content: bytes) -> bool:
        """
        Checks for multiple DQT (Define Quantization Table) markers in JPEG,
        which often occurs when an image is edited and resaved with different settings.
        JPEG DQT marker is 0xFFDB.
        """
        # Simple check: count 0xFFDB occurrences. 
        # Most cameras have 1 or 2. Editors might leave old ones or add new ones.
        # This is a simplified heuristic.
        dqt_count = content.count(b'\xFF\xDB')
        return dqt_count > 2

    def _detect_repeated_patterns(self, content: bytes) -> bool:
        """
        Very basic heuristic to detect large blocks of repeated data 
        which might indicate cloning (or just blank space).
        """
        # Skip header
        body = content[1024:]
        if len(body) < 1024:
            return False
            
        # Check for exact 64-byte block repetitions (simplified)
        # In a real system, we'd use feature matching (SIFT/SURF).
        # Here we just look for suspiciously low entropy or exact duplicates in a small sample.
        return False # Disabled for now to avoid false positives on simple files
