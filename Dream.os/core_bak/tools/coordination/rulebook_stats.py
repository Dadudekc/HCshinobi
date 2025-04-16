import os
import json
import subprocess
from datetime import datetime
import re

# --- Function to parse rulebook.md ---
def parse_rulebook(file_path):
    rules = []
    if not os.path.exists(file_path):
        print(f"❌ Rulebook file not found: {file_path}")
        return rules

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

        # Basic pattern: headings or numbered rules
        rule_pattern = re.compile(r'^\s*(?:[-*]|\d+\.)\s+(.*)', re.MULTILINE)

        for match in rule_pattern.finditer(content):
            rule_text = match.group(1).strip()
            if rule_text:
                rules.append(rule_text)
    
    return rules

# --- Function to get git commit history ---
def get_commit_history(limit=20):
    commits = []
    try:
        result = subprocess.run(
            ["git", "log", f"--pretty=format:%h|%an|%ad|%s", "--date=iso", f"-n {limit}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.split("|")
            if len(parts) == 4:
                commit = {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                }
                commits.append(commit)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting commit history: {e.stderr}")
    
    return commits

# --- Function to generate CLI summary ---
def generate_summary(rules, commits):
    summary = []
    summary.append("📘 Rulebook Summary:")
    summary.append(f"• Total rules parsed: {len(rules)}")
    if rules:
        summary.append(f"• First rule: {rules[0]}")
        summary.append(f"• Last rule: {rules[-1]}")
    
    summary.append("\n📜 Recent Commits:")
    for commit in commits[:5]:
        summary.append(f"  - [{commit['hash']}] {commit['message']} ({commit['author']}, {commit['date']})")
    
    return "\n".join(summary)

# --- Function to write JSON stats ---
def output_json_stats(rules, commits, output_path):
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "rule_count": len(rules),
        "rules": rules,
        "commit_count": len(commits),
        "commits": commits
    }
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(stats, json_file, indent=4)
    print(f"\n✅ Stats written to {output_path}")

# --- Main Execution ---
if __name__ == "__main__":
    rulebook_path = "rulebook.md"
    json_output_path = "rulebook_stats.json"

    print("📂 Parsing rulebook and extracting commit history...\n")

    rules = parse_rulebook(rulebook_path)
    commits = get_commit_history()

    summary = generate_summary(rules, commits)
    print(summary)

    output_json_stats(rules, commits, json_output_path)
