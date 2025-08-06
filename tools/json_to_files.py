import json
import re
import os

# === Prompt-Zuordnungen per Stichwort ===
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

def extract_code_blocks(text):
    return re.findall(r"```(?:[a-zA-Z]*\n)?(.*?)```", text, re.DOTALL)

def process_folder(folder_path):
    input_file = os.path.join(folder_path, "chat.json")
    if not os.path.exists(input_file):
        return

    model_path_parts = folder_path.split(os.sep)
    try:
        model_name = f"{model_path_parts[-4]}_{model_path_parts[-3]}"
        strategy = model_path_parts[-2]
        version = model_path_parts[-1]
    except IndexError:
        print(f"[!] Ungültiger Pfadaufbau: {folder_path}")
        return

    print(f"\n🔍 Modell: {model_name} | Strategie: {strategy} | Version: {version}")

    expected_files = list(PROMPT_KEYWORDS.keys())
    existing_files = [f for f in expected_files if os.path.exists(os.path.join(folder_path, f))]
    missing_files = [f for f in expected_files if f not in existing_files]

    for f in expected_files:
        if f in existing_files:
            print(f"[✓] {f}")
        else:
            print(f"[X] {f} – Generiere...")

    if not missing_files:
        return

    with open(input_file, "r", encoding="utf-8") as f:
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
            if filename in used_files or filename not in missing_files:
                continue
            match_count = sum(1 for keyword in keywords if keyword.lower() in content)
            if match_count >= 2:
                file_path = os.path.join(folder_path, filename)
                with open(file_path, "w", encoding="utf-8") as out:
                    out.write(code_blocks[0].strip())
                used_files.add(filename)
                break

def walk_llm_folders():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.abspath(os.path.join(script_dir, "..", "large-language-models", "local-llm"))

    if not os.path.exists(base_path):
        print(f"[!] Basisordner nicht gefunden: {base_path}")
        return

    for root, dirs, files in os.walk(base_path):
        if "chat.json" in files:
            process_folder(root)

if __name__ == "__main__":
    walk_llm_folders()
