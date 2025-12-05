import os
import sys
import json
import subprocess
from github import Github, Auth
from google import genai
from google.genai import Client

# Load env vars
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

# Read inputs safely
diff_path = sys.argv[1] if len(sys.argv) > 1 else None

diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print("Diff missing or too small. Unable to generate PR summary.")
    sys.exit(0)

# Run Semgrep (JSON + text)
def run_semgrep():
    json_out = "/tmp/semgrep.json"

    try:
        subprocess.run(
            [
                "semgrep", "scan",
                "--config", semgrep_config,
                "--json",
                "--output", json_out
            ],
            check=False
        )
    except Exception as e:
        return None

    if os.path.exists(json_out):
        try:
            with open(json_out, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    return None

# Convert Semgrep JSON to readable grouped text
def format_semgrep(findings):
    if not findings:
        return "No Semgrep issues found."

    grouped = {}
    for f in findings:
        sev = f.get("extra", {}).get("severity", "UNKNOWN").upper()
        grouped.setdefault(sev, []).append(f)

    output = []
    for severity in ["ERROR", "WARNING", "INFO", "UNKNOWN"]:
        if severity not in grouped:
            continue

        output.append(f"\n### {severity} Findings")
        for item in grouped[severity]:
            rule = item.get("check_id", "unknown-rule")
            msg = item.get("extra", {}).get("message", "")
            file = item.get("path", "unknown-file")
            line = item.get("start", {}).get("line", "?")

            output.append(
                f"- Rule: {rule}\n"
                f"  Message: {msg}\n"
                f"  File: {file}\n"
                f"  Line: {line}"
            )

    return "\n".join(output).strip()

# Run Semgrep
semgrep_json = run_semgrep()
findings = semgrep_json.get("results", []) if semgrep_json else []
semgrep_summary = format_semgrep(findings)

# GitHub client
gh = Github(auth=Auth.Token(github_token))
repo = gh.get_repo(repo_full)
pr = repo.get_pull(pr_number)

# LLM prompt
prompt = f"""
You are an expert technical editor and PR summarizer. Your goal is to provide a
concise, structured summary of the Pull Request based on the provided code diff.

### DIFF
{diff_content}

### SEMGREP CONFIG
{semgrep_config}

### Analysis REPORT
{semgrep_summary}

### Summary
- 2–3 bullets describing concrete changes in the diff. If changes are more, add more bullets.

### Why It Matters
- 1–2 insights grounded in diff. If changes are more, add more bullets.

### Issues
- Real issues from diff or Semgrep. Write "No issues found" if nothing.

### Verdict
- Approve / Needs Fixes / Review Required.

### Risk Level
- LOW / MEDIUM / HIGH.

### Recommendations
- Max 2 bullets based ONLY on the diff. If changes are more, add more bullets.

RULES:
- No generic text.
- No hallucinations.
- Must stay under 140 words.
- Semgrep section MUST appear in final output.
- Must not refer to tools or internal processes.
"""

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text.strip())
