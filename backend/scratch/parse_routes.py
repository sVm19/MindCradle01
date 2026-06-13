import re
import os

for filename in os.listdir("app/routers"):
    if filename.endswith(".py"):
        filepath = os.path.join("app/routers", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r"@router\.(get|post|put|delete)\(\"([^\"]+)\"", content)
        if matches:
            print(f"--- {filename} ---")
            for m in matches:
                print(f"{m[0].upper()} {m[1]}")
