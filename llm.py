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

# ---- Read DIFF INPUT ----
diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print("Diff missing or too small. Unable to generate PR summary.")
    sys.exit(0)

# ---- Read Semgrep JSON ----
semgrep_json = {}
if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
    except:
        semgrep_json = {}

findings = semgrep_json.get("results", [])

# ---- Group Semgrep Findings ----
def format_grouped_findings(results):
    if not results:
        return "No issues detected."
    
    grouped = {}
    for f in results:
        sev = f.get("extra", {}).get("severity", "UNKNOWN").upper()
        grouped.setdefault(sev, []).append(f)

    text = []
    for sev in ["ERROR", "WARNING", "INFO", "UNKNOWN"]:
        if sev not in grouped:
            continue
        text.append(f"\n### {sev} Findings")
        for item in grouped[sev]:
            text.append(
                f"- **Rule:** {item.get('check_id')}\n"
                f"  **Message:** {item.get('extra', {}).get('message', '')}\n"
                f"  **File:** {item.get('path')}\n"
                f"  **Line:** {item.get('start', {}).get('line')}"
            )
    return "\n".join(text)

analysis_summary = format_grouped_findings(findings)

# ---- Metadata Extraction ----
analysis_metadata = {
    "version": semgrep_json.get("version"),
    "configs": semgrep_json.get("configs"),
    "rules": semgrep_json.get("rules"),
    "paths_scanned": semgrep_json.get("paths", {}).get("scanned"),
    "errors": semgrep_json.get("errors"),
    "total_findings": len(findings),
}

# ---- Raw Metadata (truncated) ----
raw_meta = json.dumps(analysis_metadata, indent=2)
if len(raw_meta) > 2500:
    raw_meta = raw_meta[:2500] + "\n...(truncated)..."

# ---- PROMPT ----
prompt = f"""
You are an expert technical PR reviewer.

### DIFF
{diff_content}

---

## 🔍 ANALYSIS REPORT
{analysis_summary}

---

## 🧩 ANALYSIS METADATA
- Version: {analysis_metadata['version']}
- Configs: {analysis_metadata['configs']}
- Files Scanned: {analysis_metadata['paths_scanned']}
- Total Findings: {analysis_metadata['total_findings']}
- Errors: {analysis_metadata['errors']}

---

## 🗂 RAW ANALYSIS METADATA (for LLM context)
{raw_meta}

---

### REQUIRED OUTPUT FORMAT (max 140 words)

### Summary
- 2–3 bullets describing concrete changes. if changes are more add more bullets.

### Analysis Report
- Bullet summary of grouped findings (use ERROR, WARNING, INFO)

### Why It Matters
- Real reasoning based on diff. if changes are more add more bullets.

### Issues
- Combine analysis + real code issues. if changes are more add more bullets.

### Verdict
- Approve / Needs Fixes / Review Required

### Risk Level
- LOW / MEDIUM / HIGH

### Changes Required
- Up to 2 bullets, no generic advice. if changes are more add more bullets.

RULES:
- No hallucinations
- Must use analysis metadata
- Must use grouped analysis findings
- No references to tools
"""

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text.strip())
