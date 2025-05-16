
from utils import (
    extract_owner_and_repo,
    extract_repo_content,
    validate_project_alignment,
    generate_initial_report,
    review_report,
    revise_report,
    extract_json_from_llm_response
)
from log_utils import log_api_call,logger


@log_api_call
async def analyze_repository(github_repo, github_project_name, eval_criteria, skills):
    """Main controller function to analyze a GitHub repository."""
    try:
        # Step 1: Extract owner and repo from GitHub URL
        logger.info("Extracting owner and repo from GitHub URL")
        owner, repo = extract_owner_and_repo(github_repo)
        
        # Step 2: Extract repository content
        logger.info("Extracting repository content")
        repo_content_result = extract_repo_content(owner, repo)
        
        if repo_content_result.get("rejected", False):
            logger.warning(f"Repository rejected: {repo_content_result['rejection_reason']}")
            return {
                "status": "rejected",
                "data": {"rejection_reason": repo_content_result["rejection_reason"]},
                "message": "Repository analysis was rejected"
            }
        
        codebase = repo_content_result["codebase"]
        
        # Step 3: Validate project alignment
        logger.info("Validating project alignment")
        validation_result = validate_project_alignment(
            github_project_name, 
            eval_criteria, 
            skills, 
            codebase
        )
        
        if validation_result.get("vrejected", False):
            logger.warning(f"Validation rejected: {validation_result['rejection_reason']}")
            return {
                "status": "rejected",
                "data": {"rejection_reason": validation_result["rejection_reason"]},
                "message": "Repository validation failed"
            }
        
        # Step 4: Generate initial report
        logger.info("Generating initial report")
        initial_report = generate_initial_report(
            github_repo,
            github_project_name,
            eval_criteria,
            skills,
            codebase
        )
        
        # Step 5: Review the report
        logger.info("Reviewing report")
        review_result = review_report(
            github_repo,
            eval_criteria,
            skills,
            codebase,
            initial_report
        )
        
        # Step 6: Revise the report based on feedback
        logger.info("Revising report")
        final_report_dict = revise_report(
            github_repo,
            github_project_name,
            eval_criteria,
            skills,
            codebase,
            initial_report,
            review_result
        )


        return {
            "status": "success",
            "data": {"final_report": final_report_dict},
            "message": "Repository analysis completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing repository: {str(e)}")
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error analyzing repository: {str(e)}"
        }
