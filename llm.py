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
You are an expert PR reviewer who fully understands this repository.
You must generate highly specific feedback based only on:
- Real repository context (every file scanned automatically)
- Actual PR diff
- Semgrep metadata

Do not give generic suggestions.
Do not hallucinate missing functionality.

REPOSITORY CONTEXT (auto-scanned)
{json.dumps(repo_context, indent=2)}

PR DIFF
{diff_content}

SEMGREP METADATA
{json.dumps(analysis_metadata, indent=2)}

Your Responsibilities:
- Provide an accurate, context-aware PR review.
- Reference the specific files and logic touched in the PR.
- Explain real architectural, functional, or workflow impact.
- Identify bugs, risks, regressions, security concerns only if present.
- Do not assume behavior not shown in the repo context.
Final Output Format (max 100 words)

## Summary of Actual Changes
- Describe exactly what the PR changed with respect to repository.

## Impact on This Repository
- Explain how the changes affect workflows, functionality, or architecture with respect to repository.

## Issues / Risks Found
- Only list actual issues visible in diff or repo context .

## Required Fixes
- Only list fixes specific to this PR with respect to repository.

Do not output anything outside this format.
Do not give the output more than  100 words 
keep it small 
"""
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=Prompt,
)

print(response.text.strip())