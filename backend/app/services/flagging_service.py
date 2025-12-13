"""
Flagging Service

Identifies documents that require special attention or review based on content keywords
and metadata patterns.
"""

from typing import Dict, List, Any
import re

class FlaggingService:
    """
    Service for flagging documents based on content and metadata.
    """
    
    # Default keywords that trigger a "Review" flag
    SENSITIVE_KEYWORDS = [
        r"\bconfidential\b",
        r"\bprivileged\b",
        r"\bsecret\b",
        r"\bdo not distribute\b",
        r"\battorney-client\b",
        r"\bwork product\b",
        r"\brestricted\b",
        r"\bproprietary\b",
        r"\btrade secret\b",
        r"\bunder seal\b"
    ]

    def __init__(self):
        self.keyword_patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_KEYWORDS]

    def check_flags(self, text: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Analyzes text and metadata to return a list of flags.
        
        Args:
            text: The full text content of the document.
            metadata: The document's metadata dictionary.
            
        Returns:
            List of strings representing flags (e.g., "SENSITIVE", "privileged").
        """
        flags = []
        
        # 1. Content-based flagging
        # Check for sensitive keywords
        # We limit the check to the first 5000 characters for performance, 
        # as these warnings usually appear at the top.
        text_head = text[:5000]
        for pattern in self.keyword_patterns:
            if pattern.search(text_head):
                flags.append("SENSITIVE")
                # If we find one, we can stop checking for "SENSITIVE" to avoid duplicates,
                # unless we want specific flags for each keyword.
                # Let's add specific sub-flags if needed, but for now just "SENSITIVE".
                break
                
        # Check for specific privileged terms
        if re.search(r"\battorney-client\b", text_head, re.IGNORECASE) or \
           re.search(r"\bwork product\b", text_head, re.IGNORECASE):
            flags.append("PRIVILEGED")

        # 2. Metadata-based flagging
        # Check for high-risk file types (if not already handled by ingestion filter)
        file_ext = metadata.get("file_extension", "").lower()
        if file_ext in [".exe", ".bin", ".dll", ".bat", ".sh"]:
            flags.append("SUSPICIOUS_TYPE")
            
        # Check for large files (metadata might have size)
        # This is usually handled before, but good to flag if it slipped through
        file_size = metadata.get("file_size", 0)
        if file_size > 50 * 1024 * 1024: # 50MB
            flags.append("LARGE_FILE")

        return list(set(flags)) # Remove duplicates

# Singleton instance
_flagging_service = None

def get_flagging_service() -> FlaggingService:
    global _flagging_service
    if _flagging_service is None:
        _flagging_service = FlaggingService()
    return _flagging_service
