import os
import sys
import json
from github import Github, Auth
from google import genai

# Arguments from workflow
diff_path = sys.argv[1]
semgrep_path = sys.argv[2]

# Load diff content
with open(diff_path, "r", encoding="utf-8") as f:
    diff_content = f.read()

# Load Semgrep output
try:
    with open(semgrep_path, "r", encoding="utf-8") as f:
        semgrep_json = json.load(f)
        findings = semgrep_json.get("results", [])
        semgrep_summary = "\n".join(
            [f"- {i['check_id']}: {i['extra'].get('message','')}" for i in findings]
        ) or "No Semgrep issues found."
except:
    semgrep_summary = "Failed to parse Semgrep output."

# GH env
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")

# GitHub client
gh = Github(auth=Auth.Token(github_token))
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# Build prompt
prompt = f"""
You are an automated code reviewer with the goal of producing a short,
developer-friendly Pull Request summary (max 120 words).

### PR Title
{pr.title}

### PR Diff
{diff_content}

### Semgrep Findings
{semgrep_summary}

### Your Response Format (MANDATORY)

### Summary
- 2–3 bullets describing the most important code changes.

### Why It Matters
- 1–2 bullets explaining impact or improvements.

### Issues 
- Mention only real risks. If none, write "None".

### Verdict
- One sentence: approve, needs fixes, or review required.

### Risk Level 
- Assign a risk of LOW, MEDIUM, or HIGH based on the complexity and scope.

Rules:
- DO NOT restate the PR title or description.
- DO NOT repeat code.
- DO NOT exceed 120 words.
- Respond ONLY in clear Markdown format, using headers as listed.
"""

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text.strip())
