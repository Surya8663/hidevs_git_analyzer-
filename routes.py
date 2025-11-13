from fastapi import APIRouter, HTTPException
from models import RepositoryAnalysisRequest, RepositoryAnalysisResponse
from controller import (
    analyze_repository, 
    analyze_repository_career_focus, 
    get_career_path_suggestions, 
    analyze_multiple_career_paths,
    extract_career_insights
)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()

class RepositoryAnalysisRequest(BaseModel):
    """Request model for repository analysis."""
    github_repo: str
    github_project_name: str
    eval_criteria: str
    skills: str
    career_path: Optional[str] = None  # New field for career path

class CareerSuggestionRequest(BaseModel):
    """Request model for career path suggestions."""
    project_tech_stack: List[str]
    current_skills: List[str]

class MultipleCareerAnalysisRequest(BaseModel):
    """Request model for multiple career path analysis."""
    github_repo: str
    github_project_name: str
    eval_criteria: str
    skills: str
    career_paths: List[str]

class CareerInsightsRequest(BaseModel):
    """Request model for extracting career insights from existing report."""
    final_report: Dict[str, Any]

class CareerComparisonResponse(BaseModel):
    """Response model for career comparison."""
    status: str
    data: Dict[str, Any]
    message: Optional[str] = None

class CareerSuggestionsResponse(BaseModel):
    """Response model for career suggestions."""
    status: str
    data: Dict[str, Any]
    message: Optional[str] = None

@router.post("/analyze", response_model=RepositoryAnalysisResponse)
async def analyze_repo_endpoint(request: RepositoryAnalysisRequest):
    """
    Analyze a GitHub repository based on provided criteria and skills.
    
    Returns a detailed evaluation report if successful, or a rejection reason if the repository
    doesn't meet the basic requirements (missing README, etc.)
    
    Now includes optional career-oriented analysis when career_path is provided.
    """
    try:
        result = await analyze_repository(
            request.github_repo,
            request.github_project_name,
            request.eval_criteria,
            request.skills,
            request.career_path  # New parameter
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing repository: {str(e)}")

@router.post("/analyze/career-focused", response_model=RepositoryAnalysisResponse)
async def analyze_repo_career_focus_endpoint(request: RepositoryAnalysisRequest):
    """
    Analyze a GitHub repository with enhanced career-focused insights.
    
    This endpoint provides more detailed career-oriented analysis including:
    - Detailed career alignment metrics
    - Industry skill gap analysis
    - Career development recommendations
    - Recruitment readiness assessment
    """
    try:
        if not request.career_path:
            raise HTTPException(
                status_code=400, 
                detail="Career path is required for career-focused analysis. Use /analyze for general analysis."
            )
        
        result = await analyze_repository_career_focus(
            request.github_repo,
            request.github_project_name,
            request.eval_criteria,
            request.skills,
            request.career_path
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in career-focused analysis: {str(e)}")

@router.post("/career/suggestions", response_model=CareerSuggestionsResponse)
async def get_career_suggestions_endpoint(request: CareerSuggestionRequest):
    """
    Get career path suggestions based on project technology stack and current skills.
    
    This endpoint helps users discover which career paths align best with their
    current technologies and skills, and identifies skill gaps for each path.
    """
    try:
        if not request.project_tech_stack or not request.current_skills:
            raise HTTPException(
                status_code=400, 
                detail="Both project_tech_stack and current_skills are required"
            )
        
        result = await get_career_path_suggestions(
            request.project_tech_stack,
            request.current_skills
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating career suggestions: {str(e)}")

@router.post("/analyze/multiple-careers", response_model=CareerComparisonResponse)
async def analyze_multiple_careers_endpoint(request: MultipleCareerAnalysisRequest):
    """
    Analyze a repository against multiple career paths for comparative analysis.
    
    This endpoint provides:
    - Comparative analysis across multiple career paths
    - Career relevance scores for each path
    - Ranking of most suitable career paths
    - Detailed comparison metrics
    """
    try:
        if not request.career_paths:
            raise HTTPException(
                status_code=400, 
                detail="At least one career path is required for comparative analysis"
            )
        
        if len(request.career_paths) > 10:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 10 career paths allowed for analysis"
            )
        
        result = await analyze_multiple_career_paths(
            request.github_repo,
            request.github_project_name,
            request.eval_criteria,
            request.skills,
            request.career_paths
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multiple career analysis: {str(e)}")

@router.post("/career/insights", response_model=CareerSuggestionsResponse)
async def extract_career_insights_endpoint(request: CareerInsightsRequest):
    """
    Extract and summarize career insights from an existing analysis report.
    
    This endpoint is useful for:
    - Re-analyzing existing reports for career insights
    - Getting career-focused summaries without re-analyzing the repository
    - Comparing career aspects across different reports
    """
    try:
        if not request.final_report:
            raise HTTPException(
                status_code=400, 
                detail="final_report is required for career insights extraction"
            )
        
        insights = extract_career_insights(request.final_report)
        
        if "error" in insights:
            raise HTTPException(status_code=400, detail=insights["error"])
        
        return {
            "status": "success",
            "data": {"career_insights": insights},
            "message": "Career insights extracted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting career insights: {str(e)}")

@router.get("/career/paths")
async def get_supported_career_paths():
    """
    Get list of supported career paths for analysis.
    
    Returns a list of career paths that the system can analyze with their
    typical technology requirements and skill expectations.
    """
    supported_careers = {
        "Machine Learning Engineer": {
            "description": "Build and deploy machine learning models and systems",
            "core_technologies": ["Python", "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy"],
            "key_skills": ["ML Algorithms", "Data Preprocessing", "Model Deployment", "MLOps"],
            "industries": ["Tech", "Finance", "Healthcare", "E-commerce"]
        },
        "Data Scientist": {
            "description": "Extract insights from data using statistical and ML techniques",
            "core_technologies": ["Python", "R", "SQL", "Pandas", "Jupyter", "Tableau"],
            "key_skills": ["Statistics", "Data Visualization", "Machine Learning", "Business Analysis"],
            "industries": ["All industries with data-driven decision making"]
        },
        "Full Stack Developer": {
            "description": "Develop both frontend and backend components of web applications",
            "core_technologies": ["JavaScript", "React", "Node.js", "HTML/CSS", "Database", "REST APIs"],
            "key_skills": ["UI/UX Design", "API Development", "Database Design", "DevOps Basics"],
            "industries": ["Tech", "Startups", "E-commerce", "SaaS"]
        },
        "Backend Developer": {
            "description": "Develop server-side logic, databases, and APIs",
            "core_technologies": ["Python", "Java", "C#", "Node.js", "SQL", "NoSQL", "Docker"],
            "key_skills": ["API Design", "Database Optimization", "System Architecture", "Security"],
            "industries": ["Tech", "Finance", "Enterprise Software"]
        },
        "Frontend Developer": {
            "description": "Develop user interfaces and client-side functionality",
            "core_technologies": ["JavaScript", "TypeScript", "React", "Vue", "Angular", "HTML/CSS"],
            "key_skills": ["UI/UX Implementation", "Performance Optimization", "Cross-browser Compatibility"],
            "industries": ["Tech", "Media", "E-commerce", "SaaS"]
        },
        "DevOps Engineer": {
            "description": "Manage infrastructure, deployment, and operational processes",
            "core_technologies": ["Docker", "Kubernetes", "AWS/Azure/GCP", "Jenkins", "Terraform", "Linux"],
            "key_skills": ["CI/CD", "Infrastructure as Code", "Monitoring", "System Administration"],
            "industries": ["Tech", "Finance", "Large-scale Web Services"]
        },
        "Data Engineer": {
            "description": "Build and maintain data pipelines and infrastructure",
            "core_technologies": ["Python", "SQL", "Spark", "Hadoop", "Airflow", "Kafka", "AWS"],
            "key_skills": ["Data Modeling", "ETL Processes", "Big Data Technologies", "Data Warehousing"],
            "industries": ["Tech", "Finance", "Healthcare", "E-commerce"]
        },
        "Mobile Developer": {
            "description": "Develop applications for iOS and Android platforms",
            "core_technologies": ["Swift", "Kotlin", "React Native", "Flutter", "Java", "Objective-C"],
            "key_skills": ["Mobile UI/UX", "Platform-specific APIs", "Performance Optimization", "App Store Deployment"],
            "industries": ["Tech", "Media", "Gaming", "E-commerce"]
        },
        "Software Engineer": {
            "description": "Design, develop, and maintain software systems",
            "core_technologies": ["Java", "Python", "C++", "C#", "Go", "JavaScript", "SQL"],
            "key_skills": ["System Design", "Algorithms", "Software Architecture", "Testing", "Debugging"],
            "industries": ["All industries requiring software development"]
        },
        "Cloud Engineer": {
            "description": "Design and implement cloud infrastructure and services",
            "core_technologies": ["AWS", "Azure", "GCP", "Terraform", "Docker", "Kubernetes", "Python"],
            "key_skills": ["Cloud Architecture", "Infrastructure as Code", "Security", "Cost Optimization"],
            "industries": ["Tech", "Enterprise", "SaaS", "E-commerce"]
        }
    }
    
    return {
        "status": "success",
        "data": {
            "supported_careers": supported_careers,
            "total_careers": len(supported_careers),
            "description": "List of career paths supported for analysis with their typical requirements"
        },
        "message": "Supported career paths retrieved successfully"
    }

@router.get("/career/trends")
async def get_career_trends():
    """
    Get current trends and insights for different tech career paths.
    
    Provides information about:
    - In-demand skills for each career path
    - Salary trends
    - Job market outlook
    - Emerging technologies
    """
    career_trends = {
        "Machine Learning Engineer": {
            "in_demand_skills": ["LLM Deployment", "MLOps", "Cloud ML Services", "Explainable AI"],
            "emerging_technologies": ["Generative AI", "Federated Learning", "AutoML", "Edge AI"],
            "salary_range": "$120,000 - $250,000",
            "job_growth": "Very High",
            "remote_opportunities": "High"
        },
        "Data Scientist": {
            "in_demand_skills": ["Generative AI", "Big Data Analytics", "Business Intelligence", "Statistical Modeling"],
            "emerging_technologies": ["AI-assisted Analytics", "Real-time Data Processing", "Data Mesh Architecture"],
            "salary_range": "$100,000 - $200,000",
            "job_growth": "High",
            "remote_opportunities": "High"
        },
        "Full Stack Developer": {
            "in_demand_skills": ["React/Next.js", "TypeScript", "Cloud Deployment", "Microservices"],
            "emerging_technologies": ["Web3", "Progressive Web Apps", "Serverless Architecture"],
            "salary_range": "$80,000 - $180,000",
            "job_growth": "High",
            "remote_opportunities": "Very High"
        },
        "DevOps Engineer": {
            "in_demand_skills": ["Kubernetes", "GitOps", "Cloud Security", "Infrastructure as Code"],
            "emerging_technologies": ["Platform Engineering", "AI-powered Ops", "Edge Computing"],
            "salary_range": "$100,000 - $220,000",
            "job_growth": "Very High",
            "remote_opportunities": "High"
        },
        "Data Engineer": {
            "in_demand_skills": ["Real-time Data Processing", "Data Governance", "Cloud Data Services", "Data Quality"],
            "emerging_technologies": ["Data Mesh", "Data Fabric", "Streaming Analytics"],
            "salary_range": "$110,000 - $200,000",
            "job_growth": "High",
            "remote_opportunities": "High"
        }
    }
    
    return {
        "status": "success",
        "data": {
            "career_trends": career_trends,
            "last_updated": "2024",
            "source": "Industry analysis and job market data"
        },
        "message": "Career trends retrieved successfully"
    }

@router.post("/analyze/compare-reports")
async def compare_career_insights(reports: List[Dict[str, Any]]):
    """
    Compare career insights across multiple analysis reports.
    
    Useful for:
    - Comparing different projects for the same career path
    - Comparing the same project across different career paths
    - Tracking career development progress across multiple projects
    """
    try:
        if len(reports) < 2:
            raise HTTPException(
                status_code=400, 
                detail="At least 2 reports are required for comparison"
            )
        
        if len(reports) > 5:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 5 reports allowed for comparison"
            )
        
        comparison_results = []
        
        for i, report in enumerate(reports):
            insights = extract_career_insights(report)
            if "error" not in insights:
                comparison_results.append({
                    "report_index": i,
                    "github_project_name": report.get("report", {}).get("project_summary", {}).get("Project", f"Project_{i+1}"),
                    "career_insights": insights
                })
        
        # Calculate comparison metrics
        if len(comparison_results) >= 2:
            # Find best career alignment
            best_alignment = max(comparison_results, key=lambda x: x["career_insights"]["career_relevance_score"])
            
            # Calculate average scores
            avg_relevance = sum(r["career_insights"]["career_relevance_score"] for r in comparison_results) / len(comparison_results)
            
            comparison_summary = {
                "total_reports_compared": len(comparison_results),
                "average_career_relevance": round(avg_relevance, 2),
                "best_aligned_project": best_alignment["github_project_name"],
                "best_alignment_score": best_alignment["career_insights"]["career_relevance_score"]
            }
        else:
            comparison_summary = {"error": "Insufficient valid reports for comparison"}
        
        return {
            "status": "success",
            "data": {
                "individual_insights": comparison_results,
                "comparison_summary": comparison_summary
            },
            "message": f"Successfully compared {len(comparison_results)} reports"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing reports: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    
    Now includes information about career analysis features.
    """
    return {
        "status": "healthy", 
        "message": "GitHub Repository Analyzer API is operational",
        "features": {
            "core_analysis": "active",
            "career_analysis": "active",
            "career_suggestions": "active",
            "multiple_career_comparison": "active",
            "career_insights_extraction": "active"
        },
        "version": "2.0.0",
        "career_paths_supported": 10
    }

@router.get("/")
async def root():
    """
    Root endpoint with API information and available endpoints.
    """
    return {
        "name": "GitHub Repository Analyzer API",
        "version": "2.0.0",
        "description": "AI-powered GitHub repository analysis with career-oriented insights",
        "endpoints": {
            "core_analysis": {
                "path": "/api/v1/analyze",
                "method": "POST",
                "description": "Analyze repository with optional career path"
            },
            "career_focused_analysis": {
                "path": "/api/v1/analyze/career-focused",
                "method": "POST",
                "description": "Enhanced analysis with career-specific insights"
            },
            "career_suggestions": {
                "path": "/api/v1/career/suggestions",
                "method": "POST",
                "description": "Get career path suggestions based on tech stack"
            },
            "multiple_career_analysis": {
                "path": "/api/v1/analyze/multiple-careers",
                "method": "POST",
                "description": "Compare repository across multiple career paths"
            },
            "supported_careers": {
                "path": "/api/v1/career/paths",
                "method": "GET",
                "description": "Get list of supported career paths"
            },
            "career_trends": {
                "path": "/api/v1/career/trends",
                "method": "GET",
                "description": "Get current career market trends"
            },
            "compare_reports": {
                "path": "/api/v1/analyze/compare-reports",
                "method": "POST",
                "description": "Compare career insights across multiple reports"
            }
        },
        "documentation": "/docs",
        "career_features": [
            "Career relevance scoring",
            "Industry skill gap analysis",
            "Career development recommendations",
            "Recruitment readiness assessment",
            "Multiple career path comparison",
            "Career trend analysis"
        ]
    }