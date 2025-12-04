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

prompt = f"""
You are an automated GitHub Pull Request reviewer.

Your job is to create a short, clear summary of the PR.

Output format:
### Summary
- 2–3 bullets describing what changed.

### Why It Matters
- 1–2 bullets explaining the impact.

### Risks / Issues
- Mention only real issues (or write “None”).

### Verdict
- One sentence: approve, needs fixes, or review required.

Rules:
- Max 120 words.
- No fluff, no repetition.
- Do NOT restate commit messages or PR description.
- Use simple, developer-friendly language.
    """
# Gemini client (NEW API)
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

clean_text = response.text.strip()
print(clean_text)

print(response.text)
