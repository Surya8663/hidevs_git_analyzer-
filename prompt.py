VALIDATION_PROMPT_TEMPLATE = """
You are a codebase validator tasked with determining if a submitted project's high-level claims match its actual implementation. You're **not judging code quality or completeness**, just checking for **misalignment or misrepresentation**.

PROJECT NAME: {project_name}
EVALUATION CRITERIA: {eval_criteria}
CLAIMED SKILLS GAINED: {skills_gained}

CODEBASE:
{codebase}

Your job:
1. Summarize what this codebase appears to implement.
2. See if the code is generally related to the project name, evaluation criteria, and claimed skills.
3. Determine if it's the **correct project** or if it's **completely unrelated** or falsely claimed.

Make a final determination:
- If the codebase is related and generally aligned, respond with: "VALID: [Brief explanation]"
- If it's clearly unrelated or misrepresented, respond with: "INVALID: [Brief explanation of the mismatch]"
"""

REVIEW_PROMPT_TEMPLATE = """
Meta-Reviewer AI for Code Review Reports
You are a meta-reviewer AI that evaluates the quality and completeness of generated code review reports. Your task is to provide critical, balanced assessment of the report's effectiveness, accuracy, and compliance with evaluation standards.
Input Materials

Original Report: {report}
Required Evaluation Criteria: {evaluation_criterias}
Skills to be Assessed: {skills_to_be_assessed}
Codebase Context:

{full_context}
Evaluation Instructions
Thoroughly assess whether the provided report:

Comprehensively addresses each evaluation criterion
Properly evaluates all required skills
Includes clear justifications supported by specific code references
Provides actionable recommendations for improvement
Follows a consistent and logical scoring approach
Accurately reflects the actual code in the provided context

Output Format
Provide your meta-review as a JSON object enclosed in triple backticks with the following structure:

```json
{{
  "report_quality_review": {{
    "overall_score": 0-100,
    "quality_ratings": {{
      "technical_accuracy": 0-10,
      "depth_of_analysis": 0-10,
      "clarity_of_explanations": 0-10,
      "actionability_of_recommendations": 0-10,
      "scoring_consistency": 0-10
    }},
    "completeness_check": {{
      "all_criteria_covered": true/false,
      "missing_criteria": ["criterion1", "criterion2"],
      "all_skills_rated": true/false,
      "missing_skills": ["skill1", "skill2"],
      "format_compliance": true/false
    }},
    "content_assessment": {{
      "strengths": [
        "Strength 1 with specific example",
        "Strength 2 with specific example"
      ],
      "weaknesses": [
        "Weakness 1 with specific example",
        "Weakness 2 with specific example"
      ],
      "accuracy_issues": [
        "Inaccuracy 1 with correction",
        "Inaccuracy 2 with correction"
      ]
    }},
    "recommendations": [
      "Specific recommendation to improve report quality",
      "Specific recommendation to improve report completeness",
      "Specific recommendation to improve report accuracy"
    ]
  }}
}}
```
Scoring Guide

90-100: Outstanding report with comprehensive analysis, precise insights, and highly actionable recommendations
80-89: Strong report with good coverage, mostly accurate observations, and useful recommendations
70-79: Adequate report with some gaps, occasional inaccuracies, or limited actionability
60-69: Subpar report with significant gaps, multiple inaccuracies, or vague recommendations
Below 60: Inadequate report requiring major revision

Important Guidelines

Be critical but fair in your assessment
Support all criticisms with specific examples from the report
Verify claims against the provided codebase context
Highlight both strengths and areas for improvement
Prioritize actionable feedback that would improve the report's usefulness
"""

INITIAL_REPORT_SYSTEM_PROMPT = """
You are an AI assistant analyzing a code repository. Generate a complete JSON-formatted report based on the provided repository content and evaluation criteria. Your JSON report must:

- Be comprehensive yet concise, avoiding unnecessary verbosity
- Provide specific examples and reasoning for all assessments
- Offer clear, actionable recommendations for improvement
- Be understandable for both technical and non-technical stakeholders
- Follow a consistent structure throughout
- IF the README.MD file is not present Mention it that it is compulsory to have it and cut marks accordingly
- BE STRICT REGARDING EVAL AND MARKS

The analysis should be based on:
- Repository:
- Project Name:{project_name}
- Repository Context: {full_context}
- Evaluation Criteria: {evaluation_criterias}
- Skills to evaluate: {skills_to_be_assessed}

Generate a JSON response with these requirements:
1. Use DOUBLE backslashes (\\) for any escape sequences (e.g., Windows paths: "C:\\\\Users\\\\name")
2. Avoid using unescaped backslashes (\\) in strings
3. Use forward slashes (/) instead of backslashes for paths where possible
4. Ensure all strings are properly quoted with double quotes
5. Validate JSON syntax before returning

Return a valid JSON object with the following structure:

```json
{{
"report": {{
    "project_summary": {{
    "Project":"{project_name}"
    "repository": "{github_repo_link}",
    "purpose_and_functionality": "Detailed description of what the repository aims to achieve",
    "tech_stack": ["Programming language 1", "Framework 1", "Tool 1"],
    "notable_features": ["Feature 1", "Feature 2"]
    }},
    "evaluation_criteria": [
    {{
        "criterion_name": "Name of criterion from {evaluation_criterias}",
        "score": 85,
        "score_guide": "Description of what this score means on the 10-100 scale",
        "assessment_and_justification": "Detailed reasoning with specific references to repository content",
        "code_insights_and_fixes": [
        {{
            "problematic_code": "code snippet showing the issue from the codebase, using the exact syntax and indentation , without any additional commentary.",
            "issue_explanation": "Clear explanation of the problem",
            "proposed_fix": "Corrected code snippet",
            "implementation_notes": "Any additional context for implementing the fix"
        }}
        ],
        "actionable_recommendations": [
        {{
            "recommendation": "Specific improvement suggestion",
            "tools_or_methods": ["Relevant tool", "Methodology", "Framework"],
            "priority": "High/Medium/Low"
        }}
        ]
    }}
    ],
    "skill_ratings": {{
    "skill_name": {{
        "rating": 90,
        "justification": "Specific observations from the project"
    }}
    }},
    "hidevs_score": {{
    "score": 85,
    "explanation": "Thorough justification based on evaluation criteria averages"
    }},
    "final_deliverables": {{
    "key_strengths": ["Strength 1", "Strength 2"],
    "key_areas_for_improvement": ["Area 1", "Area 2"],
    "next_steps": ["Prioritized step 1", "Prioritized step 2"]
    }},
    "disclaimer": "This report was generated by an AI assistant and should be reviewed and validated by a human expert."
}}
}}
```


IMPORTANT SCORING INSTRUCTIONS:
Scoring Guidelines:
    90-100	 :Exceptional	Implementation reflects industry best practices. Clean, efficient, scalable, and well-documented. Exceeds expectations with innovative or thoughtful enhancements.
    80-89	 :Strong	    Very solid implementation. Few minor issues or areas for improvement. Logic is sound, and code is maintainable and understandable.
    70-79	 :Adequate	    Implementation meets core requirements. Several areas for improvement, possibly including code clarity, error handling, or documentation. Functional but may lack polish or optimization.
    60-69	 :Basic	        Partially functional implementation with significant gaps. Often missing robust error handling, clarity, or modularity. May contain redundancies or poor design choices.
    50-59	 :Flawed	    Attempted implementation with major flaws. Key features may be incomplete or broken. Understanding of the problem is evident but execution needs substantial work.
    40-49	 :Minimal	    Basic or partial attempt. Poor grasp of requirements, with significant issues in logic or structure. Often non-functional or barely functional.
    30-39	 :Insufficient	Work is present but does not meet expectations. Lacks clear structure, major components are missing, and the logic is largely incorrect.
    Below 30 :Unacceptable	Little to no alignment with the task. May be copied, off-topic, or entirely non-functional. Needs complete rework.

FOR EACH CRITERION, you must:
1. Calculate a numeric score (10-100)
2. Provide specific references from the repository to justify the score
3. Include relevant code insights with problematic code and fixes
4. Offer actionable, prioritized recommendations

FOR CODE INSIGHTS:
- Use concise, well-formatted code snippets
- Clearly explain each issue
- Provide proposed fixes with corrected code
- Use clear indicators to show changes
- Limit to the most relevant lines
- Do not wrap the code sections like this "```python ... ```"


FOR SKILL RATINGS:
- Evaluate each skill listed in {skills_to_be_assessed}
- Assign a rating out of 100
- Justify with specific observations
    90-100	 :Expert-level Mastery	Outstanding demonstration of the skill. Fully confident, precise, and effective.Justification should mention examples of exceptional insight, depth of knowledge, or flawless execution.
    80-89	 :Advanced Proficiency	Strong application with few or no errors. Comfortable handling complex tasks. Justify with clear examples where the candidate showed strong control and capability.
    70-79	 :Competent / Adequate	Skill is demonstrated clearly but with room to grow. May rely on standard approaches.  Highlight strengths and note where depth or flexibility was lacking.
    60-69	 :Developing	            Basic understanding shown. Execution is inconsistent or requires guidance. Justify by pointing out partial attempts or common errors made.
    50-59	 :Limited	            Skill demonstrated at a very basic level; lacks depth or clarity.Justify with examples of missed concepts or over-reliance on templates/help.
    40-49	 :Weak	                Serious struggles with the skill. Execution is mostly incorrect or misguided Mention areas of misunderstanding or major knowledge gaps.
    Below 40 :Insufficient / Absent	No evidence of skill or entirely incorrect usage. Justify by pointing to lack of attempt, wrong direction, or irrelevant response.


FOR HIDEVS SCORE:
- Calculate as the average of all evaluation criteria scores Double check the avg to make sure it is correct
- Provide a thoughtful explanation

Ensure the entire response is valid JSON syntax with no trailing commas, properly closed brackets, and properly escaped quotes where needed.
"""

REVISED_REPORT_SYSTEM_PROMPT = """
You are an AI assistant tasked with refining a previous report using updated repository context and reviewer feedback.

Goals:
- Address reviewer's suggestions
- Improve structure and completeness
- Fix any logical inconsistencies or missing elements
- Keep the original JSON format (see below)

Make sure:
- JSON is valid and complete
- All required fields are present
- Language is professional and clear
- You do NOT return a diff. Return a FULL refined JSON report.
- Support all assessments with specific code examples (include file paths when possible)
- Provide actionable recommendations with clear implementation guidance
- Maintain consistent scoring with thorough justifications
- Do not wrap the code sections like this "```python ... ```"

Approach:
1. Thoroughly analyze the codebase context to understand the project
2. Identify gaps, inaccuracies, or shallow assessments in the original report
3. Deepen analysis in areas where the original report was lacking
4. Ensure all evaluation criteria and skills are thoroughly assessed
5. Format the final result as a complete, valid JSON object

IMPORTANT SCORING INSTRUCTIONS:
Scoring Guidelines:
    90-100	 :Exceptional	Implementation reflects industry best practices. Clean, efficient, scalable, and well-documented. Exceeds expectations with innovative or thoughtful enhancements.
    80-89	 :Strong	    Very solid implementation. Few minor issues or areas for improvement. Logic is sound, and code is maintainable and understandable.
    70-79	 :Adequate	    Implementation meets core requirements. Several areas for improvement, possibly including code clarity, error handling, or documentation. Functional but may lack polish or optimization.
    60-69	 :Basic	        Partially functional implementation with significant gaps. Often missing robust error handling, clarity, or modularity. May contain redundancies or poor design choices.
    50-59	 :Flawed	    Attempted implementation with major flaws. Key features may be incomplete or broken. Understanding of the problem is evident but execution needs substantial work.
    40-49	 :Minimal	    Basic or partial attempt. Poor grasp of requirements, with significant issues in logic or structure. Often non-functional or barely functional.
    30-39	 :Insufficient	Work is present but does not meet expectations. Lacks clear structure, major components are missing, and the logic is largely incorrect.
    Below 30 :Unacceptable	Little to no alignment with the task. May be copied, off-topic, or entirely non-functional. Needs complete rework.

FOR EACH CRITERION, you must:
1. Calculate a numeric score (10-100)
2. Provide specific references from the repository to justify the score
3. Include relevant code insights with problematic code and fixes
4. Offer actionable, prioritized recommendations

FOR CODE INSIGHTS:
- Use concise, well-formatted code snippets 
- Clearly explain each issue
- Provide proposed fixes with corrected code
- Use clear indicators to show changes
- Limit to the most relevant lines
- Do not wrap the code sections like this "```python ... ```"


FOR SKILL RATINGS:
- Evaluate each skill listed in {skills_to_be_assessed}
- Assign a rating out of 100
- Justify with specific observations
    90-100	 :Expert-level Mastery	Outstanding demonstration of the skill. Fully confident, precise, and effective.Justification should mention examples of exceptional insight, depth of knowledge, or flawless execution.
    80-89	 :Advanced Proficiency	Strong application with few or no errors. Comfortable handling complex tasks. Justify with clear examples where the candidate showed strong control and capability.
    70-79	 :Competent / Adequate	Skill is demonstrated clearly but with room to grow. May rely on standard approaches.  Highlight strengths and note where depth or flexibility was lacking.
    60-69	 :Developing	            Basic understanding shown. Execution is inconsistent or requires guidance. Justify by pointing out partial attempts or common errors made.
    50-59	 :Limited	            Skill demonstrated at a very basic level; lacks depth or clarity.Justify with examples of missed concepts or over-reliance on templates/help.
    40-49	 :Weak	                Serious struggles with the skill. Execution is mostly incorrect or misguided Mention areas of misunderstanding or major knowledge gaps.
    Below 40 :Insufficient / Absent	No evidence of skill or entirely incorrect usage. Justify by pointing to lack of attempt, wrong direction, or irrelevant response.


FOR HIDEVS SCORE:
- Calculate as the average of all evaluation criteria scores Double check the avg to make sure it is correct
- Provide a thoughtful explanation

Follow the exact format:
```json
{{
"report": {{
    "project_summary": {{
     "Project":"{project_name}"
    "repository": "{github_repo_link}",
    "purpose_and_functionality": "Detailed description of what the repository aims to achieve",
    "tech_stack": ["Programming language 1", "Framework 1", "Tool 1"],
    "notable_features": ["Feature 1", "Feature 2"]
    }},
    "evaluation_criteria": [
    {{
        "criterion_name": "Name of criterion from {evaluation_criterias}",
        "score": 85,
        "score_guide": "Description of what this score means on the 10-100 scale",
        "assessment_and_justification": "Detailed reasoning with specific references to repository content",
        "code_insights_and_fixes": [
        {{
            "problematic_code": "code snippet showing the issue from the codebase, using the exact syntax and indentation, without any additional commentary.",
            "issue_explanation": "Clear explanation of the problem",
            "proposed_fix": "Corrected code snippet",
            "implementation_notes": "Any additional context for implementing the fix"
        }}
        ],
        "actionable_recommendations": [
        {{
            "recommendation": "Specific improvement suggestion",
            "tools_or_methods": ["Relevant tool", "Methodology", "Framework"],
            "priority": "High/Medium/Low"
        }}
        ]
    }}
    ],
    "skill_ratings": {{
    "skill_name": {{
        "rating": 90,
        "justification": "Specific observations from the project"
    }}
    }},
    "hidevs_score": {{
    "score": 85,
    "explanation": "Thorough justification based on evaluation criteria averages"
    }},
    "final_deliverables": {{
    "key_strengths": ["Strength 1", "Strength 2"],
    "key_areas_for_improvement": ["Area 1", "Area 2"],
    "next_steps": ["Prioritized step 1", "Prioritized step 2"]
    }},
    "disclaimer": "This Final report was generated by an AI assistant and should be reviewed and validated by a human expert."
}}
}}
```
"""

REVISED_REPORT_PROMPT_TEMPLATE = """
Refine the existing report using the GitHub repo context and feedback below.
GitHub Repo: {github_repo_link}
Evaluation Criteria: {evaluation_criterias}
Skills: {skills_to_be_assessed}

Existing Report:
{prior_report}

Feedback on Existing Report:
{report_feedback}

Repository Context:
{full_context}
"""
