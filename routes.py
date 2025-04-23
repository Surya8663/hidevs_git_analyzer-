from fastapi import APIRouter, HTTPException
from models import RepositoryAnalysisRequest, RepositoryAnalysisResponse
from controller import analyze_repository

router = APIRouter()

@router.post("/analyze", response_model=RepositoryAnalysisResponse)
async def analyze_repo_endpoint(request: RepositoryAnalysisRequest):
    """
    Analyze a GitHub repository based on provided criteria and skills.
    
    Returns a detailed evaluation report if successful, or a rejection reason if the repository
    doesn't meet the basic requirements (missing README, etc.)
    """
    try:
        result = await analyze_repository(
            request.github_repo,
            request.github_project_name,
            request.eval_criteria,
            request.skills
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing repository: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {"status": "healthy", "message": "GitHub Repository Analyzer API is operational"}