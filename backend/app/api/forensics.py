from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from backend.app.services.document_service import DocumentService
from backend.app.api.documents import get_document_service # Reuse dependency
from backend.app.forensics.models import ForensicAnalysisResult, CryptoTracingResult
from backend.app.forensics.analyzer import ForensicAnalyzer, get_forensic_analyzer
from backend.app.forensics.crypto_tracer import CryptoTracer, get_crypto_tracer

router = APIRouter()

@router.get(
    "/{case_id}/{doc_type}/{doc_id}/forensics",
    response_model=ForensicAnalysisResult,
    summary="Retrieve forensic analysis results for a document"
)
async def get_forensic_analysis_results(
    case_id: str,
    doc_type: str,
    doc_id: str,
    version: Optional[str] = None,
    document_service: DocumentService = Depends(get_document_service),
    forensic_analyzer: ForensicAnalyzer = Depends(get_forensic_analyzer)
):
    if doc_type != "opposition_documents":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forensic analysis is only available for opposition documents.")

    # Retrieve document content
    document_record = await document_service.get_document_content(case_id, doc_type, doc_id, version)
    if not document_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Perform forensic analysis
    # Assuming document_record.content is bytes and document_record.metadata is a dict
    forensic_results = forensic_analyzer.analyze_document(
        document_id=doc_id,
        document_content=document_record.content,
        metadata=document_record.metadata # Pass metadata if available
    )
    return forensic_results

@router.get(
    "/{case_id}/{doc_type}/{doc_id}/crypto-tracing",
    response_model=CryptoTracingResult,
    summary="Retrieve cryptocurrency tracing results for a document"
)
async def get_crypto_tracing_results(
    case_id: str,
    doc_type: str,
    doc_id: str,
    version: Optional[str] = None,
    document_service: DocumentService = Depends(get_document_service),
    crypto_tracer: CryptoTracer = Depends(get_crypto_tracer)
):
    if doc_type != "opposition_documents":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Crypto tracing is only available for opposition documents.")

    # Retrieve document content
    document_record = await document_service.get_document_content(case_id, doc_type, doc_id, version)
    if not document_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Perform crypto tracing
    # Assuming document_record.content is bytes, decode to string for crypto_tracer
    crypto_tracing_results = crypto_tracer.trace_document_for_crypto(
        document_content=document_record.content.decode('utf-8', errors='ignore'),
        document_id=doc_id
    )
    return crypto_tracing_results