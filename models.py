from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class RepositoryAnalysisRequest(BaseModel):
    """Request model for repository analysis."""
    github_repo: str
    github_project_name: str
    eval_criteria: str
    skills: str


class RepositoryAnalysisResponse(BaseModel):
    """Response model for repository analysis."""
    status: str
    data: Dict[str, Any]
    message: Optional[str] = None