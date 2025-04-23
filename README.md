# Github Repository Analysis Agent

An AI-powered tool that analyzes GitHub repositories based on custom evaluation criteria and skills assessment. This API service helps evaluate code quality, implementation completeness, and technical skill demonstration in any GitHub project.

## Features

- **Automated Repository Analysis**: Evaluate GitHub repositories against custom criteria
- **Skills Assessment**: Quantify the demonstration of technical skills within a codebase
- **Detailed Reports**: Generate comprehensive analysis with specific code insights and recommendations
- **Multi-faceted Evaluation**: Score repositories on code quality, architecture, documentation, and more
- **Actionable Feedback**: Provide concrete suggestions for improvement with code examples

## Technology Stack

- **FastAPI**: High-performance web framework for API development
- **LangChain**: Framework for LLM application development
- **Gemini AI**: Google's generative AI model for code analysis
- **GitHub API**: Access to repository content and metadata
- **Pydantic**: Data validation and settings management

## Prerequisites

- Python 3.8+
- GitHub API Token
- Google Gemini API Key


## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/github-repository-analyzer.git
   cd github-repository-analyzer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create an `.env` file with your credentials:
   ```
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_api_key
   PORT=8000
   ```

## Running the API

Start the API server:

```bash
python main.py
```

The API will be available at `http://127.0.0.1:8000` (or whichever port you specified in the `.env` file).

## API Documentation

Once the API is running, access the auto-generated documentation at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

### Health Check
```
GET /api/v1/health
```
Verifies if the API is operational.

### Analyze Repository
```
POST /api/v1/analyze
```

Request body:
```json
{
  "github_repo": "https://github.com/username/repo-name",
  "github_project_name": "Project Name",
  "eval_criteria": "Code quality, documentation, architecture",
  "skills": "Python, FastAPI, Database design"
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "final_report": {...}  // Comprehensive analysis report
  },
  "message": "Repository analysis completed successfully"
}
```

## Architecture

The project follows a layered architecture:

1. **API Layer** (`main.py`, `routes.py`): Handles HTTP requests and responses
2. **Controller Layer** (`controller.py`): Coordinates the analysis workflow
3. **Utility Layer** (`utils.py`): Contains core functionality for repository analysis
4. **Prompt Layer** (`prompt.py`): Defines AI prompts for different analysis stages
5. **Model Layer** (`models.py`): Defines data structures used throughout the application

## Analysis Workflow

1. Extract repository information from GitHub URL
2. Retrieve repository content via GitHub API
3. Validate project alignment with claimed skills and criteria
4. Generate an initial analysis report using AI
5. Review and critique the initial report
6. Generate a final, refined report based on feedback
7. Return structured analysis results

