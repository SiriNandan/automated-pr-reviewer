import os
from github import Github
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")

# GitHub client
gh = Github(github_token)
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# Collect all PR data
diff = pr.get_files()
changes_text = "\n".join([f"- {f.filename} (+{f.additions} / -{f.deletions})" for f in diff])
pr_description = pr.body or "No description provided."
title = pr.title

# Build prompt
prompt = f"""
You are an advanced code review assistant.
Generate a **medium-length detailed PR summary** including:

- PR Title
- What was changed
- Why the change matters
- Summary of added/removed files
- Potential risks
- Suggested improvements
- Any missing tests or validations

PR Title:
{title}

PR Description:
{pr_description}

Changed Files:
{changes_text}

Provide the final result in professional markdown.
"""

client = genai.Client(api_key=api_key)
result = client.generate_text(model="gemini-2.0-flash", prompt=prompt)

# Print directly → goes to GitHub Action output
print(result.text)
