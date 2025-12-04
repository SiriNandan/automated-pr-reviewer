import os
import sys
from github import Github, Auth
from google import genai
import json

# Load env vars
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

# Read inputs safely
diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print(" Diff missing or too small. Unable to generate PR summary.")
    sys.exit(0)

# Load Semgrep summary
def format_semgrep(findings):
    if not findings:
        return "No Semgrep issues found."

    formatted = []
    for f in findings:
        rule = f.get("check_id", "unknown-rule")
        msg = f.get("extra", {}).get("message", "")
        sev = f.get("extra", {}).get("severity", "UNKNOWN")
        path = f.get("path", "unknown-file")
        line = f.get("start", {}).get("line", "?")

        formatted.append(
            f"- **Rule:** {rule}\n"
            f"  **Severity:** {sev}\n"
            f"  **Message:** {msg}\n"
            f"  **Location:** {path}:{line}"
        )
    return "\n".join(formatted)

# Load Semgrep JSON
semgrep_summary = "No Semgrep issues found."
try:
    if semgrep_path and os.path.exists(semgrep_path):
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
            findings = semgrep_json.get("results", [])
            semgrep_summary = format_semgrep(findings)
except Exception as e:
    semgrep_summary = f"Semgrep error: {e}"

# GitHub client
gh = Github(auth=Auth.Token(github_token))
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# LLM prompt
prompt = f"""
You are an expert technical editor and PR summarizer. Your goal is to provide a 
concise, structured summary of the Pull Request (PR) based on the provided code diff.

### DIFF 
{diff_content}

### SEMGREP CONFIG
{semgrep_config}

### SEMGREP REPORT 
{semgrep_summary}

### Summary
- 2–3 bullets describing concrete changes in the diff. if the changes are more add more bullets but dont add more than 1 .

### Why It Matters
- 1–2 Only insights grounded in diff..  if the changes are more add more bullets but dont add more than 1.

### Issues
- Real issues from diff or Semgrep. Write "No issues found" if nothing.

### Analysis Report
(Rewrite & present the Semgrep report you received above in clean bullet style.)

### Verdict
- Approve / Needs Fixes / Review Required.

### Risk Level
- LOW / MEDIUM / HIGH.

### Recommendations
- Max 2 bullets based ONLY on the diff. if the changes are more add more bullets but dont add more than 1.

RULES:
- No generic text.
- No hallucinations.
- Must not use  any tool name or any thing working behind the scenes in the report.
- MUST stay under 140 words.
- Semgrep section MUST appear in final output.
"""

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text.strip())
