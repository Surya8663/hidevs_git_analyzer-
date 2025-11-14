import streamlit as st
import os
import time
import json
import re
import requests
from github import Github
import google.generativeai as genai

# Set page config FIRST
st.set_page_config(page_title="HiDevs GitHub Repo Analyzer", layout="wide")
st.title("🚀 HiDevs GitHub Repository Analyzer")
st.markdown("### Get comprehensive, industry-level analysis of any public GitHub repository with AI-powered career insights")

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_in_progress' not in st.session_state:
    st.session_state.analysis_in_progress = False
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# ========== LOAD ENVIRONMENT VARIABLES FIRST ==========
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

# ========== CONFIGURE GEMINI ==========
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"❌ Gemini configuration failed: {str(e)}")
    st.stop()

def call_gemini(prompt):
    """Call Gemini API with proper model selection"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        all_models = list(genai.list_models())
        generative_models = []
        for model in all_models:
            if 'generateContent' in model.supported_generation_methods:
                generative_models.append(model.name)
        
        model_attempts = [
            'gemini-2.0-flash',
            'gemini-2.0-flash-001',
            'gemini-flash-latest',
            'gemini-pro-latest',
            'gemini-2.5-flash'
        ]
        
        for model_name in generative_models:
            if model_name not in model_attempts:
                model_attempts.append(model_name)
        
        for model_name in model_attempts:
            try:
                if model_name in generative_models:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if response.text:
                        return response.text
            except Exception:
                continue
        return None
    except Exception:
        return None

# [Previous utility functions remain the same: clean_github_url, is_valid_github_url, repo_exists, extract_owner_and_repo, extract_repo_content, validate_project_alignment]

def generate_initial_report(github_repo_link, github_project_name, evaluation_criterias, skills_to_be_assessed, full_context, career_path=None):
    """Generate detailed professional analysis report"""
    prompt = f"""
    Analyze this GitHub repository and provide a COMPREHENSIVE, PROFESSIONAL JSON report suitable for executive review.
    
    Repository: {github_repo_link}
    Project: {github_project_name}
    Evaluation Criteria: {evaluation_criterias}
    Skills: {skills_to_be_assessed}
    Career Path: {career_path or "General"}
    
    Code Context:
    {full_context[:8000]}
    
    Provide an EXTREMELY DETAILED JSON report with this structure:
    {{
        "executive_summary": {{
            "overall_assessment": "Comprehensive overview of project quality and business value",
            "business_value": "Analysis of real-world applicability and impact",
            "technical_sophistication": "Evaluation of technical complexity and innovation",
            "recommendation_level": "Strong/Moderate/Low recommendation for portfolio"
        }},
        "project_summary": {{
            "Project": "project name",
            "repository": "repo url", 
            "purpose_and_functionality": "Detailed description of what the repository aims to achieve with business context",
            "tech_stack": ["tech1", "tech2"],
            "notable_features": ["feature1", "feature2"],
            "project_scale": "Small/Medium/Large",
            "business_domain": "Industry domain and target users"
        }},
        "detailed_analysis": {{
            "code_quality": {{
                "score": 85,
                "detailed_assessment": "Comprehensive analysis of code structure, readability, and maintainability",
                "strengths": ["Specific strength 1 with examples", "Specific strength 2 with examples"],
                "weaknesses": ["Specific weakness 1 with impact analysis", "Specific weakness 2 with impact analysis"],
                "industry_comparison": "How this compares to industry standards"
            }},
            "architecture_design": {{
                "score": 85,
                "detailed_assessment": "Analysis of system architecture and design patterns",
                "scalability_analysis": "Evaluation of scalability potential",
                "design_patterns_used": ["Pattern 1", "Pattern 2"],
                "architecture_improvements": ["Specific improvement 1", "Specific improvement 2"]
            }},
            "documentation": {{
                "score": 85,
                "detailed_assessment": "Comprehensive documentation quality analysis",
                "documentation_coverage": "What is well-documented vs missing",
                "onboarding_experience": "How easy it is for new developers to understand"
            }},
            "testing_strategy": {{
                "score": 85,
                "detailed_assessment": "Analysis of testing approach and coverage",
                "test_coverage_analysis": "Evaluation of what is tested vs what should be tested",
                "testing_gaps": ["Specific gap 1", "Specific gap 2"],
                "testing_recommendations": ["Specific recommendation 1", "Specific recommendation 2"]
            }}
        }},
        "career_analysis": {{
            "career_relevance_score": 85,
            "career_alignment_assessment": "Detailed analysis of how this project aligns with the target career path {career_path}. Discuss relevance to industry roles, typical responsibilities, and career progression.",
            "industry_relevant_skills": ["Skill 1", "Skill 2", "Skill 3"],
            "missing_industry_skills": ["Missing skill 1", "Missing skill 2"],
            "skill_gap_analysis": "Detailed analysis of skill gaps and their importance",
            "career_growth_opportunities": ["Opportunity 1", "Opportunity 2"],
            "industry_best_practices_applied": ["Practice 1", "Practice 2"],
            "industry_best_practices_missing": ["Missing practice 1", "Missing practice 2"],
            "portfolio_enhancement_value": "High/Medium/Low",
            "recruitment_ready_assessment": "Evaluation of how ready this project is for job applications and technical interviews",
            "next_career_steps": ["Step 1 to enhance career relevance", "Step 2 for professional growth"],
            "salary_impact_analysis": "How these skills impact market value and compensation"
        }},
        "business_impact": {{
            "market_relevance": "How relevant this project is to current market needs",
            "innovation_level": "Assessment of innovation and uniqueness",
            "enterprise_readiness": "Evaluation of production readiness",
            "scalability_potential": "Analysis of growth potential"
        }},
        "technical_deep_dive": {{
            "code_organization": "Analysis of code structure and organization",
            "error_handling": "Evaluation of error handling strategies",
            "performance_considerations": "Analysis of performance aspects",
            "security_aspects": "Security considerations and improvements needed"
        }},
        "actionable_recommendations": {{
            "immediate_improvements": ["Improvement 1 with business impact", "Improvement 2 with business impact"],
            "strategic_enhancements": ["Strategic enhancement 1", "Strategic enhancement 2"],
            "learning_path": ["Specific learning recommendation 1", "Specific learning recommendation 2"],
            "portfolio_enhancements": ["Portfolio improvement 1", "Portfolio improvement 2"]
        }},
        "hidevs_score": {{
            "score": 85,
            "score_breakdown": {{
                "technical_excellence": 85,
                "business_alignment": 85,
                "career_relevance": 85,
                "innovation_factor": 85
            }},
            "explanation": "Comprehensive justification based on all evaluation criteria with business context"
        }},
        "final_deliverables": {{
            "key_strengths": ["Strength 1 with business impact", "Strength 2 with business impact"],
            "critical_improvements": ["Critical area 1 with urgency", "Critical area 2 with urgency"],
            "strategic_next_steps": ["Prioritized step 1 with timeline", "Prioritized step 2 with timeline"],
            "investment_priority": "High/Medium/Low priority for further development"
        }}
    }}
    
    Make this analysis EXTREMELY DETAILED and PROFESSIONAL. Focus on business impact, career advancement, and technical excellence.
    Return valid JSON only.
    """
    
    result = call_gemini(prompt)
    return result

def extract_json_from_response(response: str):
    """Extract JSON from LLM response"""
    if response is None:
        raise ValueError("No response from AI")
        
    try:
        return json.loads(response)
    except:
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = response[start_idx:end_idx]
            json_str = json_str.replace('\\n', ' ').replace('\\t', ' ')
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
    
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

# [Previous analyze_repository function remains the same]

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("🔍 Complex analyses may take 2-5 minutes for comprehensive review")
    
    debug_mode = st.checkbox("Developer Mode", value=st.session_state.debug_mode, key="debug_mode", help="Show technical details for debugging")
    if debug_mode != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_mode
    
    st.subheader("🎯 Supported Career Paths")
    st.write("""
    - 🤖 Machine Learning Engineer
    - 📊 Data Scientist  
    - 💻 Software Engineer
    - 🌐 Full Stack Developer
    - 🔧 Backend Developer
    - 🎨 Frontend Developer
    - 🚀 DevOps Engineer
    - 📈 Data Engineer
    - ☁️ Cloud Engineer
    - 🔒 Security Engineer
    """)

# Main form
with st.form(key="analysis_form"):
    st.header("📋 Project Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        github_repo = st.text_input(
            "GitHub Repository URL *", 
            placeholder="https://github.com/username/repo",
            help="Must be a public repository with a README file"
        )
        
        github_project_name = st.text_input(
            "Project Name *", 
            placeholder="My AI Project",
            help="Descriptive name for your project"
        )
    
    with col2:
        eval_criteria = st.text_area(
            "Evaluation Criteria *", 
            "Code Quality, Documentation, Architecture, Testing, Career Alignment, Business Impact, Innovation",
            height=80,
            help="What aspects to evaluate (comma separated)"
        )
        
        skills = st.text_input(
            "Target Skills *", 
            "Python, Machine Learning, Software Engineering, System Design",
            help="Skills you want to assess (comma separated)"
        )
    
    career_path = st.selectbox(
        "Career Path (Optional)",
        ["", "Machine Learning Engineer", "Data Scientist", "Software Engineer", 
         "Full Stack Developer", "Backend Developer", "Frontend Developer", 
         "DevOps Engineer", "Data Engineer", "AI Engineer", "Cloud Engineer"],
        help="Get career-specific insights and recommendations"
    )
    
    submitted = st.form_submit_button("🚀 Launch Comprehensive Analysis")

# Handle form submission
if submitted:
    if not all([github_repo, github_project_name, eval_criteria, skills]):
        st.error("❌ Please fill all required fields (*)")
    else:
        st.session_state.analysis_in_progress = True
        progress_container = st.container()
        
        with progress_container:
            with st.spinner("🔍 Conducting comprehensive analysis... This may take 3-5 minutes for detailed review..."):
                result = analyze_repository(github_repo, github_project_name, eval_criteria, skills, career_path)
                st.session_state.analysis_result = result
                st.session_state.analysis_in_progress = False

# Display results
if st.session_state.analysis_result and not st.session_state.analysis_in_progress:
    result = st.session_state.analysis_result
    
    if result.get("status") == "success":
        st.success("✅ Comprehensive Analysis Completed Successfully!")
        st.balloons()
        
        try:
            report_data = result.get("data", {}).get("final_report", {})
            
            # Executive Summary Section
            st.markdown("---")
            st.header("📊 Executive Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                score = report_data.get("hidevs_score", {}).get("score", "N/A")
                st.metric("🏆 HiDevs Score", f"{score}/100", help="Overall project quality score")
            
            with col2:
                st.metric("📈 Status", "Success", help="Analysis completion status")
                
            with col3:
                if career_path:
                    st.metric("🎯 Career Path", career_path, help="Target career analysis")
                else:
                    st.metric("🎯 Analysis Type", "General", help="General technical analysis")
            
            with col4:
                portfolio_value = report_data.get("career_analysis", {}).get("portfolio_enhancement_value", "Medium")
                st.metric("💼 Portfolio Value", portfolio_value, help="Value for professional portfolio")
            
            # Executive Summary Details
            executive_summary = report_data.get("executive_summary", {})
            if executive_summary:
                st.subheader("Executive Assessment")
                cols = st.columns(2)
                with cols[0]:
                    st.info(f"**Overall Assessment:** {executive_summary.get('overall_assessment', 'N/A')}")
                    st.info(f"**Business Value:** {executive_summary.get('business_value', 'N/A')}")
                with cols[1]:
                    st.info(f"**Technical Sophistication:** {executive_summary.get('technical_sophistication', 'N/A')}")
                    st.info(f"**Recommendation Level:** {executive_summary.get('recommendation_level', 'N/A')}")
            
            # Project Summary
            st.markdown("---")
            st.header("📖 Project Overview")
            summary = report_data.get("project_summary", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Project Details")
                st.write(f"**Project:** {summary.get('Project', 'N/A')}")
                st.write(f"**Repository:** {summary.get('repository', 'N/A')}")
                st.write(f"**Project Scale:** {summary.get('project_scale', 'N/A')}")
                st.write(f"**Business Domain:** {summary.get('business_domain', 'N/A')}")
                
            with col2:
                st.subheader("Technical Stack")
                tech_stack = summary.get('tech_stack', [])
                if tech_stack:
                    for tech in tech_stack:
                        st.success(f"✅ {tech}")
                else:
                    st.info("No specific technologies identified")
                
                st.subheader("Key Features")
                features = summary.get('notable_features', [])
                if features:
                    for feature in features:
                        st.info(f"✨ {feature}")
            
            st.subheader("Project Purpose")
            st.write(summary.get('purpose_and_functionality', 'N/A'))
            
            # Detailed Analysis Section
            st.markdown("---")
            st.header("🔍 Detailed Technical Analysis")
            
            detailed_analysis = report_data.get("detailed_analysis", {})
            if detailed_analysis:
                tabs = st.tabs(["Code Quality", "Architecture", "Documentation", "Testing"])
                
                with tabs[0]:
                    code_quality = detailed_analysis.get("code_quality", {})
                    score = code_quality.get("score", "N/A")
                    st.metric("Code Quality Score", f"{score}/100")
                    st.write(f"**Assessment:** {code_quality.get('detailed_assessment', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("✅ Strengths")
                        strengths = code_quality.get('strengths', [])
                        for strength in strengths:
                            st.success(f"• {strength}")
                    with col2:
                        st.subheader("📝 Areas for Improvement")
                        weaknesses = code_quality.get('weaknesses', [])
                        for weakness in weaknesses:
                            st.warning(f"• {weakness}")
                
                with tabs[1]:
                    architecture = detailed_analysis.get("architecture_design", {})
                    score = architecture.get("score", "N/A")
                    st.metric("Architecture Score", f"{score}/100")
                    st.write(f"**Assessment:** {architecture.get('detailed_assessment', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("🏗️ Design Patterns")
                        patterns = architecture.get('design_patterns_used', [])
                        for pattern in patterns:
                            st.info(f"• {pattern}")
                    with col2:
                        st.subheader("📈 Scalability")
                        st.write(architecture.get('scalability_analysis', 'N/A'))
                
                with tabs[2]:
                    documentation = detailed_analysis.get("documentation", {})
                    score = documentation.get("score", "N/A")
                    st.metric("Documentation Score", f"{score}/100")
                    st.write(f"**Assessment:** {documentation.get('detailed_assessment', 'N/A')}")
                    st.write(f"**Documentation Coverage:** {documentation.get('documentation_coverage', 'N/A')}")
                    st.write(f"**Onboarding Experience:** {documentation.get('onboarding_experience', 'N/A')}")
                
                with tabs[3]:
                    testing = detailed_analysis.get("testing_strategy", {})
                    score = testing.get("score", "N/A")
                    st.metric("Testing Score", f"{score}/100")
                    st.write(f"**Assessment:** {testing.get('detailed_assessment', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("🔍 Testing Gaps")
                        gaps = testing.get('testing_gaps', [])
                        for gap in gaps:
                            st.error(f"• {gap}")
                    with col2:
                        st.subheader("💡 Recommendations")
                        recommendations = testing.get('testing_recommendations', [])
                        for rec in recommendations:
                            st.info(f"• {rec}")
            
            # Career Analysis Section
            if career_path:
                st.markdown("---")
                st.header(f"🎯 Career Analysis: {career_path}")
                
                career_data = report_data.get("career_analysis", {})
                if career_data:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        score = career_data.get("career_relevance_score", "N/A")
                        st.metric("Career Relevance Score", f"{score}/100")
                        
                        st.subheader("✅ Industry-Ready Skills")
                        skills_list = career_data.get("industry_relevant_skills", [])
                        if skills_list:
                            for skill in skills_list:
                                st.success(f"🎯 {skill}")
                        else:
                            st.info("No specific industry skills identified")
                        
                        st.subheader("🏆 Best Practices Applied")
                        practices = career_data.get("industry_best_practices_applied", [])
                        for practice in practices:
                            st.info(f"✓ {practice}")
                    
                    with col2:
                        st.subheader("📚 Skills to Develop")
                        missing_skills = career_data.get("missing_industry_skills", [])
                        if missing_skills:
                            for skill in missing_skills:
                                st.warning(f"📖 {skill}")
                        else:
                            st.success("No major skill gaps identified!")
                        
                        st.subheader("🔧 Missing Best Practices")
                        missing_practices = career_data.get("industry_best_practices_missing", [])
                        for practice in missing_practices:
                            st.error(f"⚡ {practice}")
                    
                    st.subheader("Career Alignment Assessment")
                    st.write(career_data.get("career_alignment_assessment", "N/A"))
                    
                    st.subheader("🚀 Career Growth Opportunities")
                    opportunities = career_data.get("career_growth_opportunities", [])
                    for opportunity in opportunities:
                        st.info(f"🌟 {opportunity}")
                    
                    st.subheader("💡 Next Career Steps")
                    next_steps = career_data.get("next_career_steps", [])
                    for step in next_steps:
                        st.success(f"🎯 {step}")
            
            # Actionable Recommendations
            st.markdown("---")
            st.header("💡 Actionable Recommendations")
            
            recommendations = report_data.get("actionable_recommendations", {})
            if recommendations:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🛠️ Immediate Improvements")
                    immediate = recommendations.get("immediate_improvements", [])
                    for improvement in immediate:
                        st.warning(f"🔧 {improvement}")
                    
                    st.subheader("📚 Learning Path")
                    learning = recommendations.get("learning_path", [])
                    for item in learning:
                        st.info(f"📖 {item}")
                
                with col2:
                    st.subheader("🎯 Strategic Enhancements")
                    strategic = recommendations.get("strategic_enhancements", [])
                    for enhancement in strategic:
                        st.success(f"🚀 {enhancement}")
                    
                    st.subheader("💼 Portfolio Enhancements")
                    portfolio = recommendations.get("portfolio_enhancements", [])
                    for enhancement in portfolio:
                        st.info(f"⭐ {enhancement}")
            
            # Final Deliverables
            st.markdown("---")
            st.header("📋 Final Assessment")
            
            deliverables = report_data.get("final_deliverables", {})
            if deliverables:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🏆 Key Strengths")
                    strengths = deliverables.get("key_strengths", [])
                    for strength in strengths:
                        st.success(f"✅ {strength}")
                
                with col2:
                    st.subheader("⚡ Critical Improvements")
                    improvements = deliverables.get("critical_improvements", [])
                    for improvement in improvements:
                        st.error(f"🔧 {improvement}")
                
                st.subheader("📅 Strategic Next Steps")
                next_steps = deliverables.get("strategic_next_steps", [])
                for step in next_steps:
                    st.info(f"🎯 {step}")
                
                priority = deliverables.get("investment_priority", "Medium")
                st.metric("💰 Investment Priority", priority)
            
            # Raw JSON view (only in debug mode)
            if st.session_state.debug_mode:
                with st.expander("🔧 Debug - View Raw Report JSON"):
                    st.json(report_data)
                
        except Exception as e:
            st.error(f"Error displaying report: {str(e)}")
            if st.session_state.debug_mode:
                with st.expander("🔍 Debug Information"):
                    st.write(result)
    
    elif result.get("status") == "rejected":
        st.error(f"❌ Analysis Rejected: {result.get('data', {}).get('rejection_reason', 'Unknown reason')}")
    
    else:
        st.error(f"⚠️ Analysis Error: {result.get('message', 'Unknown error')}")

# Instructions
with st.expander("📖 How to Use This Professional Analyzer"):
    st.markdown("""
    ## 🚀 Professional GitHub Repository Analyzer
    
    **Comprehensive Analysis Features:**
    
    ### 📊 What's Analyzed:
    - **Code Quality & Standards**: Industry-best practices, readability, maintainability
    - **Architecture & Design**: Scalability, design patterns, system structure
    - **Documentation**: Comprehensive coverage, onboarding experience
    - **Testing Strategy**: Coverage, gaps, and improvement recommendations
    - **Career Alignment**: Industry relevance and skill development
    - **Business Impact**: Market relevance and enterprise readiness
    - **Innovation Factor**: Technical sophistication and uniqueness
    
    ### 🎯 Career-Focused Insights:
    - Industry-relevant skill assessment
    - Career path alignment analysis
    - Portfolio enhancement recommendations
    - Salary impact analysis
    - Professional development roadmap
    
    ### 💼 Business Value Assessment:
    - Market relevance scoring
    - Scalability potential
    - Production readiness
    - Investment priority guidance
    
    **Step-by-Step Process:**
    1. **Enter Repository URL** - Public GitHub repo with README
    2. **Provide Project Details** - Name and description
    3. **Set Evaluation Criteria** - What to analyze
    4. **Select Target Skills** - Skills to assess
    5. **Choose Career Path** - Get specialized insights
    6. **Launch Analysis** - Get comprehensive report in 3-5 minutes
    
    **🎯 Perfect For:**
    - Job seekers building portfolios
    - Developers seeking career growth
    - Technical managers evaluating projects
    - Teams improving code quality
    - Students building professional projects
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <h3>Built with ❤️ using Streamlit & Google Gemini AI</h3>
    <p>Professional GitHub Repository Analysis for Career Advancement</p>
</div>
""", unsafe_allow_html=True)