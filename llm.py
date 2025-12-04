import os
from github import Github
from google import genai

# Load environment variables
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")

# GitHub client
gh = Github(auth=github_token)
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# Collect PR details
files = pr.get_files()
files_summary = "\n".join(
    [f"- {f.filename} (+{f.additions} / -{f.deletions})" for f in files]
)

pr_title = pr.title
pr_description = pr.body or "No description provided."

# Build Gemini prompt
prompt = f"""
You are a senior AI code reviewer. Generate a **medium-length, detailed PR summary** including:

- PR Title
- High-level explanation of what changed
- Summary of file changes
- Why the changes matter
- Potential risks
- Any missing tests or improvements

PR Title:
{pr_title}

PR Description:
{pr_description}

Changed Files:
{files_summary}

Return formatted Markdown.
"""

# Initialize Gemini client (NEW SDK)
client = genai.Client(api_key=api_key)

# Generate response using the correct API
response = client.models.generate(
    model="gemini-2.0-flash",
    prompt=prompt
)

# Print the result for GitHub Actions to capture
print(response.text)
