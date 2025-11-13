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
    clean_github_url,
    generate_career_specific_insights,
    validate_career_path,
    enhance_report_with_career_insights,
    calculate_career_relevance_metrics,
    analyze_tech_stack_for_career
)
from log_utils import log_api_call, logger
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@log_api_call
async def analyze_repository(github_repo, github_project_name, eval_criteria, skills, career_path=None):
    """Main controller function to analyze a GitHub repository with career-oriented insights."""
    try:
        # ---------------- VALIDATE AND PROCESS CAREER PATH ----------------
        career_validation = validate_career_path(career_path)
        logger.info(f"Career path validation: {career_validation['message']}")
        
        if career_path:
            logger.info(f"Career-oriented analysis requested for: {career_path}")
        
        # ---------------- CLEAN AND NORMALIZE URL ----------------
        github_repo_clean = clean_github_url(github_repo)
        logger.info(f"Cleaned GitHub URL: {github_repo_clean}")

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
            codebase,
            career_path
        )
        
        if validation_result.get("vrejected", False):
            logger.warning(f"Validation rejected: {validation_result['rejection_reason']}")
            return {
                "status": "rejected",
                "data": {"rejection_reason": validation_result["rejection_reason"]},
                "message": "Repository validation failed"
            }
        
        # ---------------- GENERATE ADDITIONAL CAREER INSIGHTS IF CAREER PATH SPECIFIED ----------------
        additional_career_insights = None
        if career_path:
            logger.info(f"Generating additional career insights for: {career_path}")
            try:
                additional_career_insights = generate_career_specific_insights(
                    github_project_name,
                    github_repo_clean,
                    codebase,
                    career_path,
                    skills
                )
                logger.info("Successfully generated additional career insights")
            except Exception as e:
                logger.warning(f"Failed to generate additional career insights: {str(e)}")
                additional_career_insights = f"Note: Additional career insights generation failed: {str(e)}"
        
        logger.info("Generating initial report")
        initial_report = generate_initial_report(
            github_repo_clean,
            github_project_name,
            eval_criteria,
            skills,
            codebase,
            career_path
        )
        
        logger.info("Reviewing report")
        review_result = review_report(
            github_repo_clean,
            eval_criteria,
            skills,
            codebase,
            initial_report,
            career_path
        )
        
        logger.info("Revising report")
        final_report_dict = revise_report(
            github_repo_clean,
            github_project_name,  # FIXED: Added missing parameter
            eval_criteria,
            skills,
            codebase,
            initial_report,
            review_result,
            career_path
        )

        # ---------------- ENHANCE FINAL REPORT WITH ADDITIONAL CAREER INSIGHTS ----------------
        if additional_career_insights and final_report_dict:
            logger.info("Enhancing final report with additional career insights")
            try:
                final_report_dict = enhance_report_with_career_insights(
                    final_report_dict, 
                    additional_career_insights
                )
            except Exception as e:
                logger.warning(f"Failed to enhance report with career insights: {str(e)}")

        # ---------------- ADD CAREER ANALYSIS METADATA ----------------
        if career_path and final_report_dict and "report" in final_report_dict:
            try:
                # Extract tech stack from project summary for career analysis
                tech_stack = final_report_dict["report"].get("project_summary", {}).get("tech_stack", [])
                
                # Calculate career relevance metrics
                career_metrics = calculate_career_relevance_metrics(
                    tech_stack=tech_stack,
                    project_complexity="medium",  # This could be enhanced with actual complexity analysis
                    skills_demonstrated=skills.split(","),
                    target_career=career_path
                )
                
                # Add career metadata to the report
                if "career_analysis" not in final_report_dict["report"]:
                    final_report_dict["report"]["career_analysis"] = {}
                
                final_report_dict["report"]["career_analysis"]["career_metrics"] = career_metrics
                final_report_dict["report"]["career_analysis"]["target_career"] = career_path
                final_report_dict["report"]["career_analysis"]["career_validation"] = career_validation
                
                logger.info(f"Added career metrics for {career_path}: {career_metrics}")
                
            except Exception as e:
                logger.warning(f"Failed to add career metadata: {str(e)}")

        # ---------------- PREPARE FINAL RESPONSE ----------------
        response_data = {"final_report": final_report_dict}
        
        # Add career-specific message if career path was provided
        message = "Repository analysis completed successfully"
        if career_path:
            message = f"Repository analysis completed successfully with career-oriented insights for {career_path}"

        return {
            "status": "success",
            "data": response_data,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error analyzing repository: {str(e)}")
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error analyzing repository: {str(e)}"
        }

@log_api_call
async def analyze_repository_career_focus(github_repo, github_project_name, eval_criteria, skills, career_path):
    """
    Specialized controller function for career-focused analysis.
    This provides more detailed career-oriented insights.
    """
    try:
        # Validate career path is provided
        if not career_path:
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Career path is required for career-focused analysis"},
                "message": "Career-focused analysis requires a specified career path"
            }
        
        # Use the main analysis function but with enhanced career focus
        result = await analyze_repository(
            github_repo,
            github_project_name,
            eval_criteria,
            skills,
            career_path
        )
        
        # If analysis was successful, enhance with additional career metrics
        if result["status"] == "success" and "final_report" in result["data"]:
            final_report = result["data"]["final_report"]
            
            # Extract tech stack for detailed career analysis
            tech_stack = final_report.get("report", {}).get("project_summary", {}).get("tech_stack", [])
            
            # Perform detailed career alignment analysis
            career_alignment = analyze_tech_stack_for_career(tech_stack, career_path)
            
            # Add detailed career alignment to the report
            if "career_analysis" not in final_report["report"]:
                final_report["report"]["career_analysis"] = {}
            
            final_report["report"]["career_analysis"]["detailed_alignment"] = career_alignment
            final_report["report"]["career_analysis"]["analysis_type"] = "career_focused"
            
            logger.info(f"Enhanced career-focused analysis for {career_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in career-focused analysis: {str(e)}")
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error in career-focused analysis: {str(e)}"
        }

@log_api_call
async def get_career_path_suggestions(project_tech_stack, current_skills):
    """
    Get career path suggestions based on project tech stack and current skills.
    This can be used to help users choose appropriate career paths.
    """
    try:
        # Common career paths with their typical requirements
        career_paths_analysis = {
            "Machine Learning Engineer": {
                "required_tech": ["Python", "TensorFlow", "PyTorch", "scikit-learn", "Pandas"],
                "alignment_score": 0,
                "skill_gaps": [],
                "recommendations": []
            },
            "Data Scientist": {
                "required_tech": ["Python", "R", "SQL", "Statistics", "Pandas", "Jupyter"],
                "alignment_score": 0,
                "skill_gaps": [],
                "recommendations": []
            },
            "Full Stack Developer": {
                "required_tech": ["JavaScript", "React", "Node.js", "HTML", "CSS", "Database"],
                "alignment_score": 0,
                "skill_gaps": [],
                "recommendations": []
            },
            "Backend Developer": {
                "required_tech": ["Python", "Java", "C#", "Node.js", "SQL", "API Design"],
                "alignment_score": 0,
                "skill_gaps": [],
                "recommendations": []
            },
            "DevOps Engineer": {
                "required_tech": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Scripting"],
                "alignment_score": 0,
                "skill_gaps": [],
                "recommendations": []
            }
        }
        
        # Calculate alignment scores for each career path
        project_tech_lower = [tech.lower() for tech in project_tech_stack]
        current_skills_lower = [skill.lower() for skill in current_skills]
        
        for career, analysis in career_paths_analysis.items():
            required_tech_lower = [tech.lower() for tech in analysis["required_tech"]]
            
            # Calculate tech alignment
            matching_tech = [tech for tech in required_tech_lower if any(proj_tech in tech or tech in proj_tech for proj_tech in project_tech_lower)]
            tech_alignment = len(matching_tech) / len(required_tech_lower) * 100
            
            # Calculate skill alignment
            matching_skills = [skill for skill in required_tech_lower if any(curr_skill in skill or skill in curr_skill for curr_skill in current_skills_lower)]
            skill_alignment = len(matching_skills) / len(required_tech_lower) * 100
            
            # Overall alignment score
            analysis["alignment_score"] = (tech_alignment + skill_alignment) / 2
            analysis["skill_gaps"] = [tech for tech in required_tech_lower if tech not in matching_skills]
            analysis["matching_technologies"] = matching_tech
            analysis["matching_skills"] = matching_skills
        
        # Sort career paths by alignment score
        sorted_careers = sorted(career_paths_analysis.items(), key=lambda x: x[1]["alignment_score"], reverse=True)
        
        return {
            "status": "success",
            "data": {
                "career_suggestions": dict(sorted_careers),
                "top_recommendation": sorted_careers[0][0] if sorted_careers else "No clear recommendation",
                "analysis_summary": f"Analyzed {len(project_tech_stack)} technologies and {len(current_skills)} skills across {len(career_paths_analysis)} career paths"
            },
            "message": "Career path suggestions generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error generating career path suggestions: {str(e)}")
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error generating career path suggestions: {str(e)}"
        }

@log_api_call
async def analyze_multiple_career_paths(github_repo, github_project_name, eval_criteria, skills, career_paths):
    """
    Analyze repository against multiple career paths for comparative analysis.
    """
    try:
        if not career_paths:
            return {
                "status": "rejected",
                "data": {"rejection_reason": "No career paths provided for analysis"},
                "message": "Please provide at least one career path for comparative analysis"
            }
        
        # Clean and validate URL
        github_repo_clean = clean_github_url(github_repo)
        
        if not is_valid_github_url(github_repo_clean):
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Invalid GitHub URL format"},
                "message": "Repository analysis was rejected due to invalid URL"
            }
        
        if not repo_exists(github_repo_clean, GITHUB_TOKEN):
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Repository not found or private"},
                "message": "Repository analysis was rejected due to inaccessible repository"
            }
        
        # Extract repository content once
        owner, repo = extract_owner_and_repo(github_repo_clean)
        repo_content_result = extract_repo_content(owner, repo)
        
        if repo_content_result.get("rejected", False):
            return {
                "status": "rejected",
                "data": {"rejection_reason": repo_content_result["rejection_reason"]},
                "message": "Repository analysis was rejected"
            }
        
        codebase = repo_content_result["codebase"]
        
        # Analyze for each career path
        career_analyses = {}
        
        for career_path in career_paths:
            logger.info(f"Analyzing for career path: {career_path}")
            
            try:
                # Generate report for this career path
                initial_report = generate_initial_report(
                    github_repo_clean,
                    github_project_name,
                    eval_criteria,
                    skills,
                    codebase,
                    career_path
                )
                
                review_result = review_report(
                    github_repo_clean,
                    eval_criteria,
                    skills,
                    codebase,
                    initial_report,
                    career_path
                )
                
                final_report = revise_report(
                    github_repo_clean,
                    github_project_name,  # FIXED: Added missing parameter
                    eval_criteria,
                    skills,
                    codebase,
                    initial_report,
                    review_result,
                    career_path
                )
                
                # Extract career relevance score
                career_score = final_report.get("report", {}).get("career_analysis", {}).get("career_relevance_score", 0)
                
                career_analyses[career_path] = {
                    "career_relevance_score": career_score,
                    "analysis_available": True,
                    "report_summary": final_report.get("report", {}).get("project_summary", {})
                }
                
            except Exception as e:
                logger.warning(f"Failed to analyze for career path {career_path}: {str(e)}")
                career_analyses[career_path] = {
                    "career_relevance_score": 0,
                    "analysis_available": False,
                    "error": str(e)
                }
        
        # Sort by career relevance score
        sorted_analyses = dict(sorted(
            career_analyses.items(), 
            key=lambda x: x[1]["career_relevance_score"], 
            reverse=True
        ))
        
        return {
            "status": "success",
            "data": {
                "career_comparison": sorted_analyses,
                "top_career_match": next(iter(sorted_analyses)) if sorted_analyses else "No clear match",
                "total_careers_analyzed": len(career_paths),
                "successful_analyses": len([ca for ca in career_analyses.values() if ca["analysis_available"]])
            },
            "message": f"Comparative analysis completed for {len(career_paths)} career paths"
        }
        
    except Exception as e:
        logger.error(f"Error in multiple career path analysis: {str(e)}")
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Error in multiple career path analysis: {str(e)}"
        }

# Helper function to extract career insights from existing report
def extract_career_insights(final_report):
    """
    Extract and summarize career insights from a completed analysis report.
    """
    try:
        if not final_report or "report" not in final_report:
            return {"error": "Invalid report format"}
        
        report_data = final_report["report"]
        career_analysis = report_data.get("career_analysis", {})
        
        insights = {
            "career_relevance_score": career_analysis.get("career_relevance_score", 0),
            "industry_skills": career_analysis.get("industry_relevant_skills", []),
            "missing_skills": career_analysis.get("missing_industry_skills", []),
            "portfolio_value": career_analysis.get("portfolio_enhancement_value", "Unknown"),
            "recruitment_ready": career_analysis.get("recruitment_ready_assessment", "Not assessed"),
            "key_strengths": report_data.get("final_deliverables", {}).get("key_strengths", []),
            "improvement_areas": report_data.get("final_deliverables", {}).get("key_areas_for_improvement", [])
        }
        
        # Generate summary assessment
        score = insights["career_relevance_score"]
        if score >= 80:
            assessment = "Excellent career alignment"
        elif score >= 70:
            assessment = "Good career alignment"
        elif score >= 60:
            assessment = "Moderate career alignment"
        else:
            assessment = "Limited career alignment"
        
        insights["summary_assessment"] = assessment
        insights["recommended_actions"] = [
            f"Focus on developing: {', '.join(insights['missing_skills'][:3])}" if insights['missing_skills'] else "No major skill gaps identified",
            f"Leverage strengths in: {', '.join(insights['key_strengths'][:3])}" if insights['key_strengths'] else "Identify project strengths",
            f"Work on: {', '.join(insights['improvement_areas'][:2])}" if insights['improvement_areas'] else "Maintain current quality standards"
        ]
        
        return insights
        
    except Exception as e:
        logger.error(f"Error extracting career insights: {str(e)}")
        return {"error": f"Failed to extract career insights: {str(e)}"}