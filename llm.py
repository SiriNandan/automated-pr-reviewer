import os
import sys
import json
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
pr_number = int(os.getenv("PR_NUMBER"))
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

semgrep_json = {}
if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
    except:
        semgrep_json = {}

analysis_metadata = {
    "version": semgrep_json.get("version"),
    "configs": semgrep_json.get("configs"),
    "rules": semgrep_json.get("rules"),
    "paths_scanned": semgrep_json.get("paths", {}).get("scanned"),
    "errors": semgrep_json.get("errors"),
    "total_findings": len(semgrep_json.get("results", [])),
}

os.makedirs("analysis_output", exist_ok=True)
with open("analysis_output/semgrep_metadata.json", "w", encoding="utf-8") as f:
    json.dump(analysis_metadata, f, indent=2)

def load_repo_context_dynamic(root="."):
    context = {}
    max_file_size = 200000            
    max_text_read = 60000             
    text_extensions = [
        ".py", ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
        ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh",
        ".ini", ".cfg", ".env"
    ]

    for dirpath, _, filenames in os.walk(root):
        if ".git" in dirpath:
            continue

        for filename in filenames:
            path = os.path.join(dirpath, filename)

            if not any(filename.endswith(ext) for ext in text_extensions):
                continue
            if os.path.getsize(path) > max_file_size:
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    context[path] = f.read()[:max_text_read]
            except:
                continue

    return context


repo_context = load_repo_context_dynamic()

Prompt = f"""
You are an expert PR reviewer with strict rules.  
You MUST generate your review ONLY from the following inputs:

1. **PR DIFF (actual code changes)**
2. **Semgrep RESULTS (raw findings — not metadata)**
3. **REPO CONTEXT (only files touched in the diff)**

You are FORBIDDEN from:
- Making assumptions about code not shown.
- Giving generic advice (e.g., “add logging”, “improve docs”).
- Mentioning best practices unless clearly violated in the diff.
- Fabricating repo structure, files, or behavior.
- Ignoring Semgrep findings.

If Semgrep finds NOTHING, you MUST say there are **no Semgrep-based issues**.

If the diff shows NO problems, you MUST say **no issues found in diff**.

Your job is to give a **compact 100-word max** review that is:
- Precise
- Based on real evidence
- Tied to specific files/lines
- Non-generic

---

## INPUT: PR DIFF
{diff_content}

## INPUT: SEMGREP FINDINGS (raw)
{json.dumps(semgrep_json.get("results", []), indent=2)}

## INPUT: REPO CONTEXT (files touched)
{json.dumps(repo_context, indent=2)}

---

## You MUST produce output EXACTLY in this format:

## Summary of Actual Changes
- State exactly what changed, referring only to diff.

## Impact on This Repository
- Describe actual effects based ONLY on visible code.

## Issues / Risks Found
- ONLY list:
  - Semgrep findings (cite rule_id)
  - Real bugs visible in diff.
- If none → write: “No issues found.”

## Required Fixes
- ONLY fixes backed by diff or Semgrep.
- Use precise file/line references when possible.
- If none → write: “No fixes required.”

You MUST stay under 100 words.
You MUST NOT add extra sections or commentary.
"""
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=Prompt,
)

print(response.text.strip())