from langchain_community.document_loaders import GithubFileLoader
from github import Github
import os
import sys
import json
import re
import requests
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from prompt import (
    VALIDATION_PROMPT_TEMPLATE,
    REVIEW_PROMPT_TEMPLATE,
    INITIAL_REPORT_SYSTEM_PROMPT,
    REVISED_REPORT_SYSTEM_PROMPT,
    REVISED_REPORT_PROMPT_TEMPLATE
)

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found. Please check your environment variables.")

if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found. Please check your environment variables.")

# Initialize LLM instances
# In utils.py - Replace the LLM initialization section
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    # Use correct model names - these are the currently available ones
    eval_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
    critique_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
    validator_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    print("Error: langchain_google_genai not installed. Please install it with pip.")
    sys.exit(1)
except Exception as e:
    print(f"Error initializing Gemini models: {str(e)}")
    # Fallback to available models
    try:
        eval_llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
        critique_llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
        validator_llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
    except:
        print("All Gemini model initialization failed")
        sys.exit(1)

# ---------------------- GITHUB VALIDATION ----------------------
GITHUB_URL_PATTERN = re.compile(
    r'^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$'
)

def clean_github_url(url: str) -> str:
    """
    Cleans and normalizes a GitHub repository URL.
    - Removes trailing .git
    - Removes trailing slashes
    - Strips /tree/... or /blob/... if present
    """
    url = url.strip()
    # Remove .git and trailing slash
    if url.endswith(".git"):
        url = url[:-4]
    url = url.rstrip("/")

    # Remove /tree/... or /blob/...
    url = re.sub(r'/(tree|blob)/.*$', '', url)

    return url

def is_valid_github_url(url: str) -> bool:
    """Check if the URL is a valid GitHub repository URL format."""
    return bool(GITHUB_URL_PATTERN.match(url))

def repo_exists(github_url: str, token: str) -> bool:
    """Check if the GitHub repository exists and is accessible."""
    owner_repo = "/".join(github_url.rstrip("/").split("/")[-2:])
    api_url = f"https://api.github.com/repos/{owner_repo}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(api_url, headers=headers)
    return response.status_code == 200

# ---------------------- EXISTING FUNCTIONS ----------------------

def extract_owner_and_repo(repo_link):
    """Extract owner and repo name from GitHub URL."""
    parts = repo_link.rstrip("/").split("/")
    
    if len(parts) < 2:
        raise ValueError("Invalid repository link format!")
    
    owner, repo = parts[-2], parts[-1]
    return owner, repo

def extract_repo_content(owner, repo):
    """Fetches repository structure and contents using GitHub API."""
    branch = "main"
    access_token = os.getenv("GITHUB_TOKEN")
    
    if not access_token:
        raise ValueError("GitHub token not found in environment variables.")
    
    g = Github(access_token)
    try:
        repo_obj = g.get_repo(f'{owner}/{repo}')
    except Exception as e:
        return {
            "rejected": True,
            "rejection_reason": f"Project rejected: Could not access repository. {str(e)}"
        }
    
    if repo_obj.private:
        return {
            "rejected": True,
            "rejection_reason": f"Project rejected: {owner}/{repo} is a private repo"
        }
    
    branch_ref = repo_obj.get_branch(branch)
    tree = repo_obj.get_git_tree(sha=branch_ref.commit.sha, recursive=True).tree
    
    # Check README existence
    readme_exists = False
    readme_content = ""
    
    for file in tree:
        if file.path.lower() in ['readme.md', 'readme', 'readme.txt']:
            readme_exists = True
            readme_file = repo_obj.get_contents(file.path)
            readme_content = readme_file.decoded_content.decode().strip()
            break
    
    if not readme_exists:
        return {
            "rejected": True,
            "rejection_reason": "Project rejected: No README file was found in the repository. Please add a README and resubmit."
        }
    
    lines = [line.strip() for line in readme_content.splitlines() if line.strip()]
    if len(readme_content) < 20 or (len(lines) == 1 and lines[0].startswith("#")):
        return {
            "rejected": True,
            "rejection_reason": "Project rejected: README file exists but is empty or uninformative. Please provide a meaningful description of your project."
        }
    
    # Generate repo structure
    repo_structure = "Repository Structure:\n"
    for file in tree:
        repo_structure += f"{file.path}\n"
    
    # Load all relevant files
    loader = GithubFileLoader(
        repo=f'{owner}/{repo}',
        access_token=access_token,
        branch=branch,
        github_api_url="https://api.github.com",
        file_filter=lambda file_path: file_path.endswith((
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.md', '.txt', '.json',
            '.yml', '.yaml', '.toml', '.ini', '.cfg', '.html', '.css', '.scss',
            '.sass', '.less', '.sql', '.sh', '.bash', '.zsh', '.fish', '.env', '.ipynb'
        )),
    )
    
    documents = loader.load()
    repo_contents = "\nRepository Contents:\n"
    for doc in documents:
        repo_contents += f"\nFile: {doc.metadata['source']}\n{doc.page_content}\n{'-'*80}\n"
    
    return {
        "rejected": False,
        "codebase": repo_structure + repo_contents
    }

def validate_project_alignment(github_project_name, eval_criteria, skills, codebase, career_path=None):
    """Validate if the project claims align with codebase."""
    validation_prompt = VALIDATION_PROMPT_TEMPLATE.format(
        github_project_name=github_project_name,
        eval_criteria=eval_criteria,
        skills_gained=skills,
        career_path=career_path or "Not specified",
        codebase=codebase
    )
    
    validation_result = validator_llm.invoke(validation_prompt).content.strip()
    
    if "INVALID:" in validation_result:
        reason = validation_result.split("INVALID:", 1)[1].strip()
        return {
            "vrejected": True,
            "rejection_reason": f"Project rejected: The project claims don't align with the codebase implementation. {reason}"
        }
    elif "VALID:" in validation_result:
        summary = validation_result.split("VALID:", 1)[1].strip()
        return {
            "vrejected": False,
            "validation_summary": summary
        }
    else:
        return {
            "vrejected": True,
            "rejection_reason": "Project rejected: The validator response did not contain a clear VALID or INVALID determination."
        }

def generate_initial_report(github_repo_link, github_project_name, evaluation_criterias, skills_to_be_assessed, full_context, career_path=None):
    """Generate initial repository analysis report."""
    sys_msg = SystemMessage(content=INITIAL_REPORT_SYSTEM_PROMPT.format(
        github_project_name=github_project_name,
        full_context=full_context,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        career_path=career_path or "Not specified",
        github_repo_link=github_repo_link
    ))
    
    query = f"github_repo_link={github_repo_link} evaluation_criterias={evaluation_criterias} skills_to_be_assessed={skills_to_be_assessed} career_path={career_path or 'Not specified'}"
    message = HumanMessage(content=query)
    
    result = eval_llm.invoke([sys_msg, message])
    return result.content  # Return raw content without JSON validation

def review_report(github_repo_link, github_project_name, evaluation_criterias, skills_to_be_assessed, full_context, report, career_path=None):
    """Review the generated report."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(
        report=report,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        full_context=full_context
    )
    
    review_result = critique_llm.invoke(review_prompt)
    return review_result.content  # Return raw content without JSON validation

def revise_report(github_repo_link, github_project_name, evaluation_criterias, skills_to_be_assessed, full_context, prior_report, report_feedback, career_path=None):
    """Revise the report based on feedback."""
    sys_msg = SystemMessage(content=REVISED_REPORT_SYSTEM_PROMPT.format(
        github_project_name=github_project_name,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        career_path=career_path or "Not specified",
        github_repo_link=github_repo_link
    ))
    
    query = REVISED_REPORT_PROMPT_TEMPLATE.format(
        github_repo_link=github_repo_link,
        github_project_name=github_project_name,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        career_path=career_path or "Not specified",
        prior_report=prior_report,
        report_feedback=report_feedback,
        full_context=full_context
    )
    
    message = HumanMessage(content=query)
    final_result = eval_llm.invoke([sys_msg, message])
    
    try:
        # First try to extract JSON
        json_content = extract_json_from_llm_response(final_result.content)
        
        # If it's a string, try to fix any malformed JSON
        if isinstance(json_content, str):
            json_content = fix_malformed_json(json_content)
            return json.loads(json_content)
        return json_content
        
    except ValueError as e:
        raise ValueError(f"Final report validation failed: {str(e)}")

def extract_json_from_llm_response(response: str):
    """
    Extracts and parses JSON from an LLM response that may contain markdown code blocks.
    Handles various JSON formatting issues.
    """
    try:
        # First try to parse the entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
            
        # Look for JSON in code blocks
        start_pattern = "```json"
        end_pattern = "```"
        
        start_idx = response.find(start_pattern)
        if start_idx == -1:
            # Try to find JSON without markdown
            start_idx = response.find('{')
            if start_idx == -1:
                raise ValueError("No JSON content found in response")
            content_start = start_idx
        else:
            content_start = start_idx + len(start_pattern)
            
        # Find the end of JSON content
        end_idx = response.rstrip().rfind(end_pattern)
        if end_idx == -1 or end_idx < content_start:
            # Look for the last closing brace
            end_idx = response.rstrip().rfind('}')
            if end_idx == -1:
                raise ValueError("No closing JSON structure found")
            json_str = response[content_start:end_idx+1].strip()
        else:
            json_str = response[content_start:end_idx].strip()
            
        # Try to fix and parse the JSON
        fixed_json = fix_malformed_json(json_str)
        return json.loads(fixed_json)
            
    except Exception as e:
        # Include part of the problematic response in the error
        preview = response[:200] + "..." if len(response) > 200 else response
        raise ValueError(f"Failed to extract valid JSON from response: {str(e)}\nResponse preview: {preview}")

def fix_malformed_json(json_str: str) -> str:
    """
    Attempts to fix common JSON formatting issues and malformed JSON structures.
    Returns the fixed JSON string or raises ValueError if unfixable.
    """
    try:
        # First try to parse as-is
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        fixed = json_str
        
        # Remove any markdown code block markers
        fixed = re.sub(r'```json\s*', '', fixed)
        fixed = re.sub(r'\s*```', '', fixed)
        
        # Fix common JSON syntax issues
        # Fix missing quotes around property names
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*?)(\s*:)', r'\1"\2"\3', fixed)
        
        # Fix trailing commas in objects/arrays
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # Fix missing commas between array/object elements
        fixed = re.sub(r'([\]"}])\s*([\[{"])', r'\1,\2', fixed)
        
        # Fix missing quotes around string values
        fixed = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_\s-]*?)([,}\]])', r':"\1"\2', fixed)
        
        # Fix escaped quotes within strings
        fixed = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)":\s*"([^"]*[^\\])"([^"]*)"', r'"\1":"\2\\"\\3"', fixed)
        
        # Remove any non-JSON text before the first { and after the last }
        start_idx = fixed.find('{')
        end_idx = fixed.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            fixed = fixed[start_idx:end_idx]
        
        try:
            # Validate the fixed JSON
            json.loads(fixed)
            return fixed
        except json.JSONDecodeError as e:
            # Provide more context in the error message
            error_context = fixed[max(0, e.pos-50):min(len(fixed), e.pos+50)]
            raise ValueError(f"Could not fix malformed JSON near: ...{error_context}... \nError: {str(e)}")

def generate_career_specific_insights(github_project_name, github_repo_link, codebase, career_path, skills_to_be_assessed):
    """
    Generate career-specific insights for the project analysis.
    This function can be called to get additional career-focused analysis.
    """
    from prompt import CAREER_SPECIFIC_INSIGHTS_TEMPLATE
    
    career_prompt = CAREER_SPECIFIC_INSIGHTS_TEMPLATE.format(
        career_path=career_path,
        github_project_name=github_project_name,
        github_repo_link=github_repo_link,
        skills_to_be_assessed=skills_to_be_assessed
    )
    
    # Combine with codebase context
    full_prompt = f"{career_prompt}\n\nCODEBASE CONTEXT:\n{codebase}"
    
    try:
        career_insights = eval_llm.invoke(full_prompt).content
        return career_insights
    except Exception as e:
        logger.error(f"Error generating career insights: {str(e)}")
        return f"Career insights generation failed: {str(e)}"

def validate_career_path(career_path):
    """
    Validate if the provided career path is supported and provide suggestions if needed.
    """
    common_career_paths = [
        "Machine Learning Engineer", "Data Scientist", "Software Engineer", 
        "Full Stack Developer", "Frontend Developer", "Backend Developer",
        "DevOps Engineer", "Data Engineer", "Mobile Developer", "AI Engineer",
        "Cloud Engineer", "Security Engineer", "QA Engineer", "Product Manager",
        "Technical Lead", "System Architect"
    ]
    
    if not career_path:
        return {
            "valid": True,
            "message": "No career path specified - analysis will be general",
            "suggestions": common_career_paths
        }
    
    # Check if career path is in common list (case-insensitive)
    career_lower = career_path.lower()
    matched_careers = [career for career in common_career_paths if career_lower in career.lower()]
    
    if matched_careers:
        return {
            "valid": True,
            "message": f"Career path '{career_path}' is recognized",
            "matched_careers": matched_careers
        }
    else:
        return {
            "valid": True,  # Still valid, just not in common list
            "message": f"Career path '{career_path}' is not in common list but will be used for analysis",
            "suggestions": common_career_paths
        }

def enhance_report_with_career_insights(report_dict, career_insights):
    """
    Enhance the existing report dictionary with additional career insights.
    """
    if not career_insights or "report" not in report_dict:
        return report_dict
    
    # Add career insights as a separate section
    if "career_analysis" not in report_dict["report"]:
        report_dict["report"]["career_analysis"] = {}
    
    report_dict["report"]["career_analysis"]["additional_insights"] = career_insights
    
    return report_dict

def calculate_career_relevance_metrics(tech_stack, project_complexity, skills_demonstrated, target_career):
    """
    Calculate career relevance metrics based on project characteristics.
    This is a helper function for career analysis.
    """
    # Base metrics (these would be enhanced with more sophisticated analysis)
    metrics = {
        "technical_alignment": 0,
        "skill_coverage": 0,
        "project_scope": 0,
        "industry_relevance": 0,
        "portfolio_impact": 0
    }
    
    # Common career-tech mappings (simplified)
    career_tech_mappings = {
        "Machine Learning Engineer": ["python", "tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy"],
        "Data Scientist": ["python", "r", "sql", "pandas", "numpy", "matplotlib", "seaborn"],
        "Software Engineer": ["java", "python", "javascript", "c++", "c#", "go", "rust"],
        "Full Stack Developer": ["javascript", "react", "angular", "vue", "node.js", "python", "django", "flask"],
        "Frontend Developer": ["javascript", "typescript", "react", "angular", "vue", "html", "css"],
        "Backend Developer": ["java", "python", "node.js", "c#", "go", "sql", "nosql"],
        "DevOps Engineer": ["docker", "kubernetes", "aws", "azure", "gcp", "jenkins", "terraform"],
        "Data Engineer": ["python", "sql", "spark", "hadoop", "airflow", "kafka", "aws"]
    }
    
    # Calculate technical alignment
    target_techs = career_tech_mappings.get(target_career, [])
    tech_stack_lower = [tech.lower() for tech in tech_stack]
    
    matching_techs = [tech for tech in target_techs if tech in ' '.join(tech_stack_lower).lower()]
    metrics["technical_alignment"] = min(100, len(matching_techs) / max(1, len(target_techs)) * 100)
    
    # Calculate skill coverage (simplified)
    metrics["skill_coverage"] = min(100, len(skills_demonstrated) * 10)
    
    # Project scope assessment
    if project_complexity == "high":
        metrics["project_scope"] = 90
    elif project_complexity == "medium":
        metrics["project_scope"] = 70
    else:
        metrics["project_scope"] = 50
    
    # Industry relevance (placeholder - would be enhanced with real data)
    metrics["industry_relevance"] = 75
    
    # Portfolio impact
    metrics["portfolio_impact"] = (metrics["technical_alignment"] + metrics["skill_coverage"] + metrics["project_scope"]) / 3
    
    return metrics

# Import logger if not already imported
try:
    from log_utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Career analysis helper functions
def analyze_tech_stack_for_career(tech_stack, career_path):
    """
    Analyze how well the technology stack aligns with the target career path.
    """
    # Industry-standard tech stacks for different careers
    industry_standards = {
        "Machine Learning Engineer": {
            "core": ["Python", "TensorFlow", "PyTorch", "scikit-learn"],
            "data": ["Pandas", "NumPy", "SQL", "Spark"],
            "deployment": ["Docker", "Kubernetes", "FastAPI", "Flask"],
            "cloud": ["AWS", "GCP", "Azure", "MLflow"]
        },
        "Data Scientist": {
            "core": ["Python", "R", "SQL", "Statistics"],
            "analysis": ["Pandas", "NumPy", "Jupyter", "Matplotlib"],
            "ml": ["scikit-learn", "TensorFlow", "PyTorch", "XGBoost"],
            "visualization": ["Tableau", "PowerBI", "Seaborn", "Plotly"]
        },
        "Full Stack Developer": {
            "frontend": ["JavaScript", "React", "Vue", "Angular", "HTML5", "CSS3"],
            "backend": ["Node.js", "Python", "Java", "C#", "Go"],
            "database": ["SQL", "MongoDB", "PostgreSQL", "Redis"],
            "devops": ["Docker", "Git", "CI/CD", "AWS"]
        },
        "Software Engineer": {
            "languages": ["Java", "Python", "C++", "C#", "Go", "Rust"],
            "concepts": ["OOP", "Design Patterns", "Data Structures", "Algorithms"],
            "tools": ["Git", "Docker", "Jenkins", "JIRA"],
            "testing": ["Unit Testing", "Integration Testing", "TDD"]
        }
    }
    
    career_standards = industry_standards.get(career_path, {})
    
    if not career_standards:
        return {"alignment": 50, "matched_technologies": [], "missing_core": []}
    
    # Calculate alignment
    matched_techs = []
    missing_core = []
    
    for category, expected_techs in career_standards.items():
        for tech in expected_techs:
            # Check if technology is in project stack (case-insensitive)
            tech_lower = tech.lower()
            project_techs_lower = [t.lower() for t in tech_stack]
            
            # Check for partial matches (e.g., "react" in "react.js")
            matched = any(tech_lower in project_tech or project_tech in tech_lower 
                         for project_tech in project_techs_lower)
            
            if matched:
                matched_techs.append(tech)
            elif category == "core":
                missing_core.append(tech)
    
    total_expected = sum(len(techs) for techs in career_standards.values())
    alignment_score = (len(matched_techs) / total_expected * 100) if total_expected > 0 else 0
    
    return {
        "alignment_score": min(100, alignment_score),
        "matched_technologies": matched_techs,
        "missing_core_technologies": missing_core,
        "coverage_by_category": {
            category: len([tech for tech in techs if tech in matched_techs]) / len(techs) * 100
            for category, techs in career_standards.items()
        }
    }