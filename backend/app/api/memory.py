from fastapi import APIRouter, Depends
from typing import Dict, Any

from backend.app.memory_store import CaseMemoryStore

router = APIRouter()

def get_store() -> CaseMemoryStore:
    return CaseMemoryStore()

@router.get('/memory/{case_id}')
async def get_memory(case_id: str, store: CaseMemoryStore = Depends(get_store)) -> Dict[str, Any]:
    return store.load(case_id)

@router.post('/memory/{case_id}')
async def set_memory(case_id: str, payload: Dict[str, Any], store: CaseMemoryStore = Depends(get_store)) -> Dict[str, Any]:
    store.save(case_id, payload)
    return payload
