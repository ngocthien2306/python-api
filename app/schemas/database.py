from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class OperationResult(BaseModel):
    type: str
    result: Dict[str, Any]

class ProcessingResults(BaseModel):
    session_id: str
    operations: List[OperationResult]

class APIResponse(BaseModel):
    success: bool
    results: Optional[ProcessingResults] = None
    error: Optional[str] = None
    partial_results: Optional[ProcessingResults] = None
