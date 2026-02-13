import json
with open("data/collected_submissions.json", "r", encoding="utf-8") as f:
    data = json.load(f)
for sub in data["submissions"]:
    if sub["track"] == "reasoning-agents":
        has_readme = bool(sub.get("readme_content"))
        has_demo = sub.get("has_demo", False)
        desc_len = len(sub.get("description", ""))
        techs = len(sub.get("technologies", []))
        num = sub["issue_number"]
        name = sub["project_name"]
        print("{} {}: readme={}, demo={}, desc={}, techs={}".format(num, name, has_readme, has_demo, desc_len, techs))
