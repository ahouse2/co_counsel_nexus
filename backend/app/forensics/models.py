from pydantic import BaseModel, Field
from typing import List, Optional

class TamperScoreResult(BaseModel):
    score: float = Field(..., description="A score indicating the probability of document tampering (0.0 to 1.0).")
    details: str = Field(..., description="Detailed explanation of the tamper score.")
    flags: List[str] = Field(default_factory=list, description="List of specific tampering indicators found.")

class ElaResult(BaseModel):
    ela_score: float = Field(..., description="Error Level Analysis score.")
    ela_heatmap_url: Optional[str] = Field(None, description="URL to the ELA heatmap image.")
    details: str = Field(..., description="Interpretation of the ELA result.")

class CloneSplicingResult(BaseModel):
    detected: bool = Field(..., description="True if clone or splicing detected.")
    details: str = Field(..., description="Details about detected clone/splicing.")
    regions: List[str] = Field(default_factory=list, description="List of regions where tampering was detected.")

class FontObjectAnalysisResult(BaseModel):
    inconsistencies_detected: bool = Field(..., description="True if font or object inconsistencies detected.")
    details: str = Field(..., description="Details about font and object inconsistencies.")
    anomalies: List[str] = Field(default_factory=list, description="List of specific anomalies found.")

class AntiScanAlterRescanResult(BaseModel):
    detected: bool = Field(..., description="True if scan-alter-rescan pattern detected.")
    details: str = Field(..., description="Details about the detected pattern.")

class ForensicAnalysisResult(BaseModel):
    document_id: str
    tamper_score: TamperScoreResult
    ela_analysis: Optional[ElaResult] = None
    clone_splicing_detection: Optional[CloneSplicingResult] = None
    font_object_analysis: Optional[FontObjectAnalysisResult] = None
    anti_scan_alter_rescan: Optional[AntiScanAlterRescanResult] = None
    overall_verdict: str = Field(..., description="Overall verdict on document authenticity.")
