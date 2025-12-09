import os
import sys
import json
from google import genai

# ENV VARS
api_key = os.getenv("GEMINI_API_KEY")
repo_full = os.getenv("REPO_FULL_NAME")
pr_number = int(os.getenv("PR_NUMBER"))
github_token = os.getenv("GITHUB_TOKEN")
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

# INPUT FILES
diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

# READ PR DIFF
diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print("Diff missing or too small. Unable to generate PR summary.")
    sys.exit(0)

# READ SEMGREP JSON
semgrep_json = {}
if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
    except:
        semgrep_json = {}

# EXTRACT ONLY METADATA
analysis_metadata = {
    "version": semgrep_json.get("version"),
    "configs": semgrep_json.get("configs"),
    "rules": semgrep_json.get("rules"),
    "paths_scanned": semgrep_json.get("paths", {}).get("scanned"),
    "errors": semgrep_json.get("errors"),
    "total_findings": len(semgrep_json.get("results", [])),
}

raw_meta = json.dumps(analysis_metadata, indent=2)

# WRITE METADATA ONLY JSON
os.makedirs("analysis_output", exist_ok=True)

metadata_file = "analysis_output/semgrep_metadata.json"
with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(analysis_metadata, f, indent=2)

print(f"Saved Semgrep metadata → {metadata_file}")

# LLM SYSTEM PROMPT FOR PR COMMENT
SystemPrompt = f"""
You are an expert technical PR reviewer.

### DIFF
{diff_content}

---

## METADATA
{raw_meta}

---

### REQUIRED OUTPUT FORMAT (max 140 words)

### Summary
- 2–3 bullets describing concrete changes.

### Why It Matters
- Real reasoning based on diff.

### Issues
- Real issues from diff.

### Changes Required
- 1–2 essential fixes.

RULES:
- No hallucinations
- No guessing
- Use ONLY the diff + metadata
"""

# CALL GEMINI
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=SystemPrompt
)

final_output = response.text.strip()
print(final_output)
