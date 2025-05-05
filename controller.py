import json
from utils import (
    extract_owner_and_repo,
    extract_repo_content,
    validate_project_alignment,
    generate_initial_report,
    review_report,
    revise_report,
    extract_json_from_llm_response
)

async def analyze_repository(github_repo, github_project_name, eval_criteria, skills):
    """
    Main controller function to analyze a GitHub repository.
    
    Args:
        github_repo: GitHub repository URL
        github_project_name: Name of the project
        eval_criteria: Evaluation criteria for the project
        skills: Skills to be assessed
        
    Returns:
        Dictionary containing analysis results or rejection reason
    """
    try:
        # Step 1: Extract owner and repo from GitHub URL
        owner, repo = extract_owner_and_repo(github_repo)
        
        # Step 2: Extract repository content
        repo_content_result = extract_repo_content(owner, repo)
        
        # Check if repository was rejected (missing README, etc.)
        if repo_content_result.get("rejected", False):
            return {
                "status": "rejected",
                "data": {"rejection_reason": repo_content_result["rejection_reason"]},
                "message": "Repository analysis was rejected"
            }
        
        codebase = repo_content_result["codebase"]
        
        # Step 3: Validate project alignment
        validation_result = validate_project_alignment(
            github_project_name, 
            eval_criteria, 
            skills, 
            codebase
        )
        
        # Check if project was rejected during validation
        if validation_result.get("vrejected", False):
            return {
                "status": "rejected",
                "data": {"rejection_reason": validation_result["rejection_reason"]},
                "message": "Repository validation failed"
            }
        
        # Step 4: Generate initial report
        initial_report = generate_initial_report(
            github_repo,
            github_project_name,
            eval_criteria,
            skills,
            codebase
        )
        
        # Step 5: Review the report
        review_result = review_report(
            github_repo,
            eval_criteria,
            skills,
            codebase,
            initial_report
        )
        
        # Step 6: Revise the report based on feedback
        final_report = revise_report(
            github_repo,
            github_project_name,
            eval_criteria,
            skills,
            codebase,
            initial_report,
            review_result
        )
        
        # Step 7: Extract JSON from the final report if needed
        final_report_json = extract_json_from_llm_response(final_report)
        final_report_json = json.loads(final_report_json)
        
        return {
            "status": "success",
            "data": {"final_report": final_report_json},
            "message": "Repository analysis completed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error analyzing repository: {str(e)}"
        }
