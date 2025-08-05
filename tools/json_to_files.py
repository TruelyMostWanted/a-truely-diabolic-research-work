import json
import re
import os

# === Konfiguration ===
INPUT_FILE = "chat.json"

# Deine fixen Prompt-Zuordnungen per Stichwort
PROMPT_KEYWORDS = {
    "p1_optimization_problem.csv": ["optimization problem", "Rank, Type/Name", "Linear Programming"],
    "p2_development_scrum.csv": ["scrum", "Step, Description, Interval", "Sprint"],
    "p3_nlp_pequirements.csv": ["natural language processing", "Keyword, Category", "RelevantScrumEntities"],
    "p4_stress_pressure.csv": ["cognitive pressure", "Influence", "AffectedEntities"],
    "p6_goals_and_conditions.csv": ["main goals", "CriteriaType", "Must-Match"],
    "p7_decision_vairables.csv": ["decision variables", "Type, Domain", "Related Entities"],
    "p9_optimization_problem.tex": ["optimization model", "\\documentclass", "\\section{Sets}"],
    "p10_graph.mmd": ["mermaid", "graph LR", "classDef entity"]
}

# === Hilfsfunktion: Extrahiere alle Codeblöcke (CSV, Mermaid, LaTeX usw.) ===
def extract_code_blocks(text):
    return re.findall(r"```(?:[a-zA-Z]*\n)?(.*?)```", text, re.DOTALL)

# === Hauptfunktion ===
def extract_outputs():
    if not os.path.exists(INPUT_FILE):
        print(f"[!] Datei '{INPUT_FILE}' nicht gefunden.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data[0]["chat"]["history"]["messages"]
    used_files = set()

    for msg in messages.values():
        if msg.get("role") != "assistant":
            continue

        content = msg.get("content", "").lower()
        code_blocks = extract_code_blocks(msg.get("content", ""))

        if not code_blocks:
            continue

        for filename, keywords in PROMPT_KEYWORDS.items():
            if filename in used_files:
                continue
            match_count = sum(1 for keyword in keywords if keyword.lower() in content)
            if match_count >= 2:
                with open(filename, "w", encoding="utf-8") as out:
                    out.write(code_blocks[0].strip())
                    print(f"[✓] Gespeichert in: {filename}")
                used_files.add(filename)
                break

if __name__ == "__main__":
    extract_outputs()
