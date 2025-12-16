from pydantic import BaseModel, Field
from typing import List, Optional

class TamperScoreResult(BaseModel):
    score: float = Field(..., description="A score indicating the probability of document tampering (0.0 to 1.0).")
    details: str = Field(..., description="Detailed explanation of the tamper score.")
    flags: List[str] = Field(default_factory=list, description="List of specific tampering indicators found.")

class ScreeningResult(BaseModel):
    is_suspicious: bool = Field(..., description="True if the document is flagged as suspicious.")
    reason: str = Field(..., description="Reason for flagging the document.")
    score: float = Field(..., description="Screening score (0.0 to 1.0).")

class ElaResult(BaseModel):
    ela_score: float = Field(..., description="Error Level Analysis score.")
    ela_heatmap_url: Optional[str] = Field(None, description="URL to the ELA heatmap image.")
    details: str = Field(..., description="Interpretation of the ELA result.")

class CloneSplicingResult(BaseModel):
    detected: bool = Field(..., description="True if clone or splicing detected.")
    details: str = Field(..., description="Details about detected clone/splicing.")
    regions: List[str] = Field(default_factory=list, description="List of regions where tampering was detected.")

class PdfStructureAnalysisResult(BaseModel):
    inconsistencies_detected: bool = Field(..., description="True if structural inconsistencies detected.")
    details: str = Field(..., description="Details about the analysis.")
    anomalies: List[str] = Field(default_factory=list, description="List of specific anomalies found.")
    incremental_updates_detected: bool = Field(False, description="True if multiple EOF markers found.")
    metadata_inconsistencies: List[str] = Field(default_factory=list, description="List of metadata mismatches.")
    suspicious_tags: List[str] = Field(default_factory=list, description="List of suspicious PDF tags found.")

class AntiScanAlterRescanResult(BaseModel):
    detected: bool = Field(..., description="True if scan-alter-rescan pattern detected.")
    details: str = Field(..., description="Details about the detected pattern.")
    moire_detected: bool = Field(False, description="True if Moiré patterns (double halftoning) are detected.")
    digital_overlays_detected: bool = Field(False, description="True if 'digital silence' (zero noise regions) is detected.")

class ForensicAnalysisResult(BaseModel):
    document_id: str
    tamper_score: TamperScoreResult
    ela_analysis: Optional[ElaResult] = None
    clone_splicing_detection: Optional[CloneSplicingResult] = None
    pdf_structure_analysis: Optional[PdfStructureAnalysisResult] = None
    anti_scan_alter_rescan: Optional[AntiScanAlterRescanResult] = None
    overall_verdict: str = Field(..., description="Overall verdict on document authenticity.")

class WalletAddress(BaseModel):
    address: str
    blockchain: str
    currency: str
    is_valid: bool = False # Added validation status

class Transaction(BaseModel):
    tx_id: str
    sender: str
    receiver: str
    amount: float
    currency: str
    timestamp: str
    blockchain: str
    # Add more fields as needed for detailed transaction data

class CryptoTracingResult(BaseModel):
    wallets_found: List[WalletAddress] = Field(default_factory=list)
    transactions_traced: List[Transaction] = Field(default_factory=list)
    visual_graph_mermaid: Optional[str] = Field(None, description="Mermaid diagram definition for the transaction graph.")
    details: str = Field(..., description="Summary of the crypto tracing analysis.")
