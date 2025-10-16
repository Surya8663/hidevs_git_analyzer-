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

# Initialize LLM instances
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    eval_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
    critique_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
    validator_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    print("Error: langchain_google_genai not installed. Please install it with pip.")
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
    return result.content  # Return raw content without JSON validation

def review_report(github_repo_link, evaluation_criterias, skills_to_be_assessed, full_context, report):
    """Review the generated report."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(
        report=report,
        evaluation_criterias=evaluation_criterias,
        skills_to_be_assessed=skills_to_be_assessed,
        full_context=full_context
    )
    
    review_result = critique_llm.invoke(review_prompt)
    return review_result.content  # Return raw content without JSON validation

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

import json
import re

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
