from utils import (
    extract_owner_and_repo,
    extract_repo_content,
    validate_project_alignment,
    generate_initial_report,
    review_report,
    revise_report,
    extract_json_from_llm_response,
    is_valid_github_url,
    repo_exists,
    clean_github_url
)
from log_utils import log_api_call, logger
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@log_api_call
async def analyze_repository(github_repo, github_project_name, eval_criteria, skills):
    """Main controller function to analyze a GitHub repository."""
    try:
        # ---------------- CLEAN AND NORMALIZE URL ----------------
        github_repo_clean = clean_github_url(github_repo)

        # ---------------- VALIDATE URL FORMAT ----------------
        if not is_valid_github_url(github_repo_clean):
            logger.warning(f"Invalid GitHub URL format after cleaning: {github_repo_clean}")
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Invalid GitHub URL. Please provide a repository URL like https://github.com/username/repo"},
                "message": "Repository analysis was rejected due to invalid URL"
            }

        # ---------------- CHECK REPOSITORY EXISTENCE ----------------
        if not repo_exists(github_repo_clean, GITHUB_TOKEN):
            logger.warning(f"Repository does not exist or is private: {github_repo_clean}")
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Repository not found or private. Please check the GitHub URL or token permissions."},
                "message": "Repository analysis was rejected due to inaccessible repository"
            }

        # ---------------- EXISTING ANALYSIS WORKFLOW ----------------
        logger.info("Extracting owner and repo from GitHub URL")
        owner, repo = extract_owner_and_repo(github_repo_clean)
        
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
        
        logger.info("Generating initial report")
        initial_report = generate_initial_report(
            github_repo_clean,
            github_project_name,
            eval_criteria,
            skills,
            codebase
        )
        
        logger.info("Reviewing report")
        review_result = review_report(
            github_repo_clean,
            eval_criteria,
            skills,
            codebase,
            initial_report
        )
        
        logger.info("Revising report")
        final_report_dict = revise_report(
            github_repo_clean,
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