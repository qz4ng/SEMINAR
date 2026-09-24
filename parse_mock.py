import re
import os
import json

with open("docs/ui/MOCK_DATA.md", "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to extract filename from "§X. `filename`" and the following JSON block
# Looking for lines like "## §1. `runs.json` — "
pattern = re.compile(r"##\s*§\d+\.\s*`([^`]+)`.*?\n```json\n(.*?)\n```", re.DOTALL)
matches = pattern.findall(content)

for filename, json_str in matches:
    if filename == "runs.json":
        path = "ui/run-viewer/src/mock/runs.json"
    elif filename == "params.json":
        path = "ui/run-viewer/src/mock/params.json"
    elif filename == "variable_roles.json":
        path = "ui/run-viewer/src/mock/variable_roles.json"
    elif filename == "artifacts_preview.json":
        path = "ui/run-viewer/src/mock/artifacts_preview.json"
    elif filename == "modules.json":
        path = "ui/run-viewer/src/content/modules.json"
    elif filename == "error_codes.json":
        path = "ui/run-viewer/src/content/error_codes.json"
    elif filename == "param_docs.json":
        path = "ui/run-viewer/src/content/param_docs.json"
    else:
        continue
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as out_f:
        out_f.write(json_str.strip())
        
    print(f"Extracted {filename} to {path}")
