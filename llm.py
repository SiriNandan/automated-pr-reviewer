import os
from github import Github, Auth
from google import genai

# Environment variables from GitHub Actions
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")

# GitHub client
gh = Github(auth=Auth.Token(github_token))
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# Get file list
files = pr.get_files()
files_summary = "\n".join(
    [f"- {f.filename} (+{f.additions} / -{f.deletions})" for f in files]
)

pr_title = pr.title
pr_description = pr.body or "No description provided."

# Build LLM prompt
prompt = f"""
You are an expert PR reviewer.
Write a medium-length but detailed PR summary including:

- What the PR changes
- Why these changes matter
- Summary of added/removed/updated files
- Potential risks
- Suggestions for improvement
- Missing tests or validations

PR Title:
{pr_title}

PR Description:
{pr_description}

Changed Files:
{files_summary}

Respond in clean GitHub Markdown.
"""

# Gemini client (NEW API)
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text)
