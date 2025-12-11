import os
import sys
import json
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
pr_raw = os.getenv("PR_NUMBER")

pr_number = int(pr_raw) if pr_raw and pr_raw.isdigit() else -1
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print("Diff missing or too small. Exiting.")
    sys.exit(0)

def compress_semgrep(full):
    results = full.get("results", [])
    compressed = []

    for r in results:
        compressed.append({
            "rule": r.get("check_id"),
            "severity": r.get("extra", {}).get("severity"),
            "message": r.get("extra", {}).get("message"),
            "path": r.get("path"),
            "line": r.get("start", {}).get("line"),
        })

    return compressed


semgrep_json = {}
compressed_findings = []

if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
            compressed_findings = compress_semgrep(semgrep_json)
    except:
        compressed_findings = []


def extract_changed_files(diff):
    files = set()
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.add(line.replace("+++ b/", "").strip())
        elif line.startswith("--- a/"):
            files.add(line.replace("--- a/", "").strip())
    return list(files)


changed_files = extract_changed_files(diff_content)
repo_context = {}
for file in changed_files:
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                repo_context[file] = f.read()[:4000]  # Limit for token savings
        except:
            continue

Prompt = f"""
You are an expert PR reviewer.
ONLY use the following inputs:
- PR DIFF
- Compressed Semgrep Findings
- Repo context for changed files

Forbidden:
- Assumptions about unseen code
- Generic advice
- Mentioning tools
- Adding new sections
- Fabrication of code or impact

Max length: 100 words.

---

## DIFF
{diff_content}

## SEMGREP FINDINGS
{json.dumps(compressed_findings, indent=2)}

## REPO CONTEXT (only changed files)
{json.dumps(repo_context, indent=2)}

---

OUTPUT EXACTLY IN THIS FORMAT:

## Impact
- give 1 to 2 buillet points for  Actual effects based ONLY on diff.

## Issues / Risks Found
- Semgrep findings (rule)
- Real bugs from diff
- If none: “No issues found.”
- give 2 to 4 buillet points 

## Required Fixes
- Only fixes backed by diff or Semgrep
- If none: “No fixes required.”
- give 1 to 2 buillet points 

## Summary
- Exact description of what changed.
- give 2 to 4 buillet points 
"""

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=Prompt,
)

print(response.text.strip())
