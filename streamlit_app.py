import streamlit as st
import os
import time
import json
import re
import requests
from github import Github
import google.generativeai as genai

# Set page config FIRST
st.set_page_config(page_title="HiDevs GitHub Agent", layout="wide")
st.title("HiDevs GitHub Repo Analyzer 🤖")
st.markdown("Get an industry-level review of any public GitHub repository with career-focused insights.")

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_in_progress' not in st.session_state:
    st.session_state.analysis_in_progress = False

# ========== LOAD ENVIRONMENT VARIABLES FIRST ==========
# Load environment variables from Streamlit secrets
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Please add GITHUB_TOKEN and GEMINI_API_KEY to Streamlit secrets")
    st.stop()

if not GEMINI_API_KEY:
    st.error("❌ GEMINI_API_KEY not found. Please check your environment variables.")
    st.stop()

if not GITHUB_TOKEN:
    st.error("❌ GITHUB_TOKEN not found. Please check your environment variables.")
    st.stop()

# ========== NOW CONFIGURE GEMINI ==========
# Configure with explicit version
genai.configure(
    api_key=GEMINI_API_KEY,
    client_options={
        'api_endpoint': 'https://generativelanguage.googleapis.com/v1beta'  # or /v1
    }
)

# Simple Gemini function with correct model names
def call_gemini(prompt):
    """Simple function to call Gemini API with correct model names"""
    try:
        # Try the latest model names first
        available_models = [
            'gemini-1.5-pro',
            'gemini-1.5-flash', 
            'gemini-pro',
            'models/gemini-pro'  # Some versions need this format
        ]
        
        for model_name in available_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Model {model_name} failed: {str(e)}")
                continue
        
        # If all models fail, raise error
        raise Exception("All Gemini models failed. Please check your API key and model availability.")
        
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return None

def check_available_models():
    """Check which Gemini models are available with the current API key"""
    try:
        available_models = genai.list_models()
        model_names = [model.name for model in available_models]
        print("Available models:", model_names)
        return model_names
    except Exception as e:
        print(f"Error checking available models: {str(e)}")
        return []       

# Temporary test function
def test_gemini_connection():
    """Test if Gemini API is working"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Hello World'")
        print("Gemini test successful:", response.text)
        return True
    except Exception as e:
        print("Gemini test failed:", str(e))
        return False

# Call this at startup
test_gemini_connection()

# Utility functions
def clean_github_url(url: str) -> str:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    url = url.rstrip("/")
    url = re.sub(r'/(tree|blob)/.*$', '', url)
    return url

def is_valid_github_url(url: str) -> bool:
    pattern = re.compile(r'^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$')
    return bool(pattern.match(url))

def extract_owner_and_repo(repo_link):
    parts = repo_link.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid repository link format!")
    owner, repo = parts[-2], parts[-1]
    return owner, repo

def extract_repo_content(owner, repo):
    """Extract repository content using simple GitHub API calls"""
    try:
        g = Github(GITHUB_TOKEN)
        repo_obj = g.get_repo(f'{owner}/{repo}')
        
        if repo_obj.private:
            return {"rejected": True, "rejection_reason": "Repository is private"}
        
        # Check README
        readme_exists = False
        readme_content = ""
        try:
            readme_file = repo_obj.get_contents("README.md")
            readme_content = readme_file.decoded_content.decode().strip()
            readme_exists = True
        except:
            pass
        
        if not readme_exists:
            return {"rejected": True, "rejection_reason": "No README.md file found"}
        
        if len(readme_content) < 20:
            return {"rejected": True, "rejection_reason": "README is too short or uninformative"}
        
        # Get basic file structure
        repo_contents = "Repository Structure:\n"
        try:
            contents = repo_obj.get_contents("")
            for content_file in contents:
                if content_file.type == "file":
                    repo_contents += f"File: {content_file.path}\n"
                    # Get content of key files
                    if content_file.path.endswith(('.py', '.js', '.md', '.json', '.yml', '.yaml')):
                        try:
                            file_content = repo_obj.get_contents(content_file.path)
                            file_text = file_content.decoded_content.decode()
                            # Limit file content to avoid huge responses
                            repo_contents += f"Content (first 2000 chars):\n{file_text[:2000]}\n"
                        except:
                            repo_contents += "[Content not accessible]\n"
                    repo_contents += "-" * 50 + "\n"
                elif content_file.type == "dir":
                    repo_contents += f"Directory: {content_file.path}/\n"
        except Exception as e:
            repo_contents += f"Error reading repository structure: {str(e)}\n"
        
        return {
            "rejected": False,
            "codebase": f"README:\n{readme_content}\n\n{repo_contents}"
        }
        
    except Exception as e:
        return {"rejected": True, "rejection_reason": f"Could not access repository: {str(e)}"}

def validate_project_alignment(github_project_name, eval_criteria, skills, codebase, career_path=None):
    """Validate if project claims align with codebase"""
    validation_prompt = f"""
    Check if this GitHub project matches its description.
    
    Project: {github_project_name}
    Criteria: {eval_criteria}
    Skills: {skills}
    Career: {career_path or "General"}
    
    Codebase Preview:
    {codebase[:4000]}
    
    Respond with ONLY:
    VALID: [reason] 
    or 
    INVALID: [reason]
    """
    
    validation_result = call_gemini(validation_prompt)
    
    if validation_result is None:
        return {"vrejected": True, "rejection_reason": "AI service unavailable"}
    
    validation_result = validation_result.strip()
    
    if validation_result.startswith("INVALID:"):
        reason = validation_result[8:].strip()
        return {"vrejected": True, "rejection_reason": reason}
    elif validation_result.startswith("VALID:"):
        return {"vrejected": False, "validation_summary": validation_result}
    else:
        # If format is wrong but content suggests validity, continue
        if "invalid" in validation_result.lower() or "reject" in validation_result.lower():
            return {"vrejected": True, "rejection_reason": f"Validation failed: {validation_result}"}
        else:
            # Be permissive and continue with analysis
            return {"vrejected": False, "validation_summary": "Proceeding with analysis"}

def generate_initial_report(github_repo_link, github_project_name, evaluation_criterias, skills_to_be_assessed, full_context, career_path=None):
    """Generate initial analysis report"""
    prompt = f"""
    Analyze this GitHub repository and provide a JSON report.
    
    Repository: {github_repo_link}
    Project: {github_project_name}
    Evaluation: {evaluation_criterias}
    Skills: {skills_to_be_assessed}
    Career: {career_path or "General"}
    
    Code Context:
    {full_context[:6000]}
    
    Provide JSON with this structure:
    {{
        "project_summary": {{
            "Project": "project name",
            "repository": "repo url", 
            "purpose_and_functionality": "description",
            "tech_stack": ["tech1", "tech2"],
            "notable_features": ["feature1", "feature2"]
        }},
        "evaluation_criteria": [
            {{
                "criterion_name": "criteria name",
                "score": 85,
                "assessment_and_justification": "detailed reasoning"
            }}
        ],
        "skill_ratings": {{
            "skill_name": {{
                "rating": 90,
                "justification": "reasoning"
            }}
        }},
        "career_analysis": {{
            "career_relevance_score": 85,
            "industry_relevant_skills": ["skill1", "skill2"],
            "missing_industry_skills": ["skill1", "skill2"]
        }},
        "hidevs_score": {{
            "score": 85,
            "explanation": "overall assessment"
        }},
        "final_deliverables": {{
            "key_strengths": ["strength1", "strength2"],
            "key_areas_for_improvement": ["area1", "area2"],
            "next_steps": ["step1", "step2"]
        }}
    }}
    
    Return valid JSON only.
    """
    
    result = call_gemini(prompt)
    return result

def extract_json_from_response(response: str):
    """Extract JSON from LLM response"""
    if response is None:
        raise ValueError("No response from AI")
        
    try:
        # Try to parse directly
        return json.loads(response)
    except:
        # Extract JSON from code blocks
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = response[start_idx:end_idx]
            # Clean up common JSON issues
            json_str = json_str.replace('\\n', ' ').replace('\\t', ' ')
            return json.loads(json_str)
    
    # If still fails, create a basic report
    return {
        "project_summary": {
            "Project": "Analysis Report",
            "repository": "Unknown",
            "purpose_and_functionality": "Analysis completed",
            "tech_stack": [],
            "notable_features": []
        },
        "hidevs_score": {
            "score": 50,
            "explanation": "Basic analysis completed"
        },
        "final_deliverables": {
            "key_strengths": ["Analysis completed successfully"],
            "key_areas_for_improvement": ["Full detailed analysis unavailable"],
            "next_steps": ["Review the raw analysis above"]
        }
    }

# Main analysis function
def analyze_repository(github_repo, github_project_name, eval_criteria, skills, career_path=None):
    """Main analysis function that runs entirely in Streamlit"""
    try:
        # Clean and validate URL
        github_repo_clean = clean_github_url(github_repo)
        if not is_valid_github_url(github_repo_clean):
            return {
                "status": "rejected",
                "data": {"rejection_reason": "Invalid GitHub URL format"},
                "message": "Invalid repository URL"
            }
        
        # Extract repo content
        st.info("📦 Extracting repository content...")
        owner, repo = extract_owner_and_repo(github_repo_clean)
        repo_content = extract_repo_content(owner, repo)
        
        if repo_content.get("rejected"):
            return {
                "status": "rejected",
                "data": {"rejection_reason": repo_content["rejection_reason"]},
                "message": "Repository access failed"
            }
        
        # Validate project alignment
        st.info("🔍 Validating project alignment...")
        validation = validate_project_alignment(
            github_project_name, eval_criteria, skills, 
            repo_content["codebase"], career_path
        )
        
        if validation.get("vrejected"):
            return {
                "status": "rejected", 
                "data": {"rejection_reason": validation["rejection_reason"]},
                "message": "Project validation failed"
            }
        
        # Generate report
        st.info("📊 Generating analysis report...")
        initial_report = generate_initial_report(
            github_repo_clean, github_project_name, eval_criteria,
            skills, repo_content["codebase"], career_path
        )
        
        if initial_report is None:
            return {
                "status": "error",
                "data": {"error": "AI service unavailable"},
                "message": "Report generation failed"
            }
        
        # Extract JSON from report
        try:
            report_json = extract_json_from_response(initial_report)
            
            return {
                "status": "success",
                "data": {"final_report": report_json},
                "message": "Analysis completed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "data": {"error": f"Failed to parse report: {str(e)}"},
                "message": "Report parsing failed"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "data": {"error": str(e)},
            "message": f"Analysis error: {str(e)}"
        }

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Complex analyses may take 2-5 minutes")
    
    st.subheader("Supported Career Paths")
    st.write("""
    - Machine Learning Engineer
    - Data Scientist  
    - Software Engineer
    - Full Stack Developer
    - Backend Developer
    - Frontend Developer
    - DevOps Engineer
    - Data Engineer
    """)

# Main form
with st.form(key="analysis_form"):
    st.header("📋 Project Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        github_repo = st.text_input(
            "GitHub Repository URL *", 
            placeholder="https://github.com/username/repo"
        )
        
        github_project_name = st.text_input(
            "Project Name *", 
            placeholder="My AI Project"
        )
    
    with col2:
        eval_criteria = st.text_area(
            "Evaluation Criteria *", 
            "Code Quality, Documentation, Architecture, Testing, Career Alignment",
            height=80
        )
        
        skills = st.text_input(
            "Target Skills *", 
            "Python, Machine Learning, Software Engineering"
        )
    
    career_path = st.selectbox(
        "Career Path (Optional)",
        ["", "Machine Learning Engineer", "Data Scientist", "Software Engineer", 
         "Full Stack Developer", "Backend Developer", "Frontend Developer", 
         "DevOps Engineer", "Data Engineer", "AI Engineer"]
    )
    
    submitted = st.form_submit_button("🚀 Analyze Repository")

# Handle form submission
if submitted:
    if not all([github_repo, github_project_name, eval_criteria, skills]):
        st.error("❌ Please fill all required fields (*)")
    else:
        st.session_state.analysis_in_progress = True
        
        with st.spinner("🔍 Analyzing repository... This may take 2-5 minutes..."):
            result = analyze_repository(github_repo, github_project_name, eval_criteria, skills, career_path)
            st.session_state.analysis_result = result
            st.session_state.analysis_in_progress = False

# Display results
if st.session_state.analysis_result and not st.session_state.analysis_in_progress:
    result = st.session_state.analysis_result
    
    if result.get("status") == "success":
        st.success("✅ Analysis completed successfully!")
        
        try:
            report_data = result.get("data", {}).get("final_report", {})
            
            # Display key metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                score = report_data.get("hidevs_score", {}).get("score", "N/A")
                st.metric("HiDevs Score", f"{score}/100")
            
            with col2:
                st.metric("Status", "Success")
                
            with col3:
                if career_path:
                    st.metric("Career Path", career_path)
            
            # Display project summary
            st.subheader("📖 Project Summary")
            summary = report_data.get("project_summary", {})
            st.write(f"**Project:** {summary.get('Project', 'N/A')}")
            st.write(f"**Repository:** {summary.get('repository', 'N/A')}")
            st.write(f"**Purpose:** {summary.get('purpose_and_functionality', 'N/A')}")
            
            # Display tech stack
            tech_stack = summary.get('tech_stack', [])
            if tech_stack:
                st.write("**Tech Stack:**", ", ".join(tech_stack))
            
            # Display career analysis if available
            if career_path and "career_analysis" in report_data:
                st.subheader(f"🎯 Career Analysis for {career_path}")
                career = report_data["career_analysis"]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**✅ Strengths:**")
                    skills_list = career.get("industry_relevant_skills", [])
                    if skills_list:
                        for skill in skills_list[:5]:
                            st.success(f"- {skill}")
                    else:
                        st.info("No specific strengths identified")
                
                with col2:
                    st.write("**📚 To Improve:**")
                    skills_list = career.get("missing_industry_skills", [])
                    if skills_list:
                        for skill in skills_list[:5]:
                            st.warning(f"- {skill}")
                    else:
                        st.info("No major improvements needed")
            
            # Display evaluation criteria
            if "evaluation_criteria" in report_data:
                st.subheader("📊 Evaluation Results")
                for criteria in report_data["evaluation_criteria"]:
                    with st.expander(f"{criteria.get('criterion_name', 'Criteria')} - Score: {criteria.get('score', 'N/A')}/100"):
                        st.write(criteria.get('assessment_and_justification', 'No details available'))
            
            # Raw JSON view
            with st.expander("📊 View Raw Report JSON"):
                st.json(report_data)
                
        except Exception as e:
            st.error(f"Error displaying report: {str(e)}")
            with st.expander("🔍 Debug Information"):
                st.write(result)
    
    elif result.get("status") == "rejected":
        st.error(f"❌ Analysis Rejected: {result.get('data', {}).get('rejection_reason', 'Unknown reason')}")
    
    else:
        st.error(f"⚠️ Analysis Error: {result.get('message', 'Unknown error')}")

# Instructions
with st.expander("📖 How to Use This Tool"):
    st.markdown("""
    **Step-by-Step Guide:**
    
    1. **Enter GitHub Repository URL** - Must be a public repository
    2. **Provide Project Name** - Descriptive name for your project  
    3. **Set Evaluation Criteria** - What aspects to evaluate
    4. **Specify Target Skills** - Skills you want to assess
    5. **Select Career Path** (Optional) - Get career-specific insights
    6. **Click Analyze** - Wait 2-5 minutes for comprehensive analysis
    
    **Requirements:**
    - ✅ Repository must be public
    - ✅ Must have README.md file
    - ✅ Valid GitHub URL format
    
    **What's Analyzed:**
    - Code quality and structure
    - Documentation completeness
    - Project architecture
    - Career relevance
    - Industry best practices
    - Skill demonstration
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit & Google Gemini AI")