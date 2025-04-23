from langchain_community.document_loaders import GithubFileLoader
from github import Github
import os
import sys
import json
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

# Initialize LLM instances
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    eval_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-03-25", google_api_key=os.getenv("GEMINI_API_KEY"))
    critique_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-03-25", google_api_key=os.getenv("GEMINI_API_KEY"))
    validator_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-03-25", google_api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    print("Error: langchain_google_genai not installed. Please install it with pip.")
    sys.exit(1)

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
    repo_obj = g.get_repo(f'{owner}/{repo}')
    
    if repo_obj.private:
        raise ValueError(f'{owner}/{repo} is a private repo')
    
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
    
    # Heuristic: if content is < 20 characters or only contains a single heading, mark as empty
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

def validate_project_alignment(project_name, eval_criteria, skills, codebase):
    """Validate if the project claims align with codebase."""
    validation_prompt = VALIDATION_PROMPT_TEMPLATE.format(
        project_name=project_name,
        eval_criteria=eval_criteria,
        skills_gained=skills,
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

def generate_initial_report(github_repo_link, project_name, evaluation_criterias, skills_to_be_assessed, full_context):
    """Generate initial repository analysis report."""
    sys_msg = SystemMessage(content=INITIAL_REPORT_SYSTEM_PROMPT.format(
        project_name=project_name,
        full_context=full_context,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        github_repo_link=github_repo_link
    ))
    
    query = f"github_repo_link={github_repo_link} evaluation_criterias={evaluation_criterias} skills_to_be_assessed={skills_to_be_assessed}"
    message = HumanMessage(content=query)
    
    result = eval_llm.invoke([sys_msg, message])
    return result.content

def review_report(github_repo_link, evaluation_criterias, skills_to_be_assessed, full_context, report):
    """Review the generated report."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(
        report=report,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        full_context=full_context
    )
    
    review_result = critique_llm.invoke(review_prompt)
    return review_result.content

def revise_report(github_repo_link, project_name, evaluation_criterias, skills_to_be_assessed, full_context, prior_report, report_feedback):
    """Revise the report based on feedback."""
    sys_msg = SystemMessage(content=REVISED_REPORT_SYSTEM_PROMPT.format(
        project_name=project_name,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        github_repo_link=github_repo_link
    ))
    
    query = REVISED_REPORT_PROMPT_TEMPLATE.format(
        github_repo_link=github_repo_link,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        prior_report=prior_report,
        report_feedback=report_feedback,
        full_context=full_context
    )
    
    message = HumanMessage(content=query)
    final_result = eval_llm.invoke([sys_msg, message])
    
    # Extract JSON content
    content = final_result.content
    if "```json" in content:
        json_part = content.split("```json")[1].split("```")[0].strip()
        return json_part
    
    return content

def extract_json_from_llm_response(response_content):
    """Extract JSON from LLM response that might contain markdown code blocks."""
    if "```json" in response_content:
        json_part = response_content.split("```json")[1].split("```")[0].strip()
        return json_part
    return response_content