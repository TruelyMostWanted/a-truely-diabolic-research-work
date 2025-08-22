# tools/json_to_files.py
import json
import re
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# ---------- Strategie-spezifische Ziel-Dateien + Heuristiken ----------

S1_FILES: Dict[str, List[str]] = {
    # Dateiname -> (mind. 2) Keywords als Fallback
    "optimization_categories.csv": ["optimization", "Rank", "Name", "Appearances"],
    "scrum_steps.csv": ["scrum", "Step", "Description", "Interval"],
    "nlp_requirements.csv": ["natural language processing", "Keyword", "Category", "Relevant"],
    "stress_pressure.csv": ["pressure", "Influence", "AffectedEntities"],
}

S23_FILES: Dict[str, List[str]] = {
    "Goals.csv": ["Goals.csv"],  # Header-Erkennung übernimmt den Rest
    "Conditions.csv": ["Conditions.csv"],
    "DecisionVariables.csv": ["DecisionVariables.csv"],
    "optimization_model.tex": ["\\documentclass", "\\section"],
    "domain_graph.mmd": ["mermaid", "graph TD", "graph LR"],
}

# CSV Header (exakt oder case-insensitive trim-match)
CSV_HEADERS = {
    "Goals.csv": "ID,Name,Description,IsSum,GoalType,EntityName,EntityAttribute,CriteriaType,Weight",
    "Conditions.csv": "ID,Name,Description,IsSum,GoalType,EntityName,EntityAttribute,CriteriaType,Weight",
    "DecisionVariables.csv": "ID,Name,Description,DataType,Domain,MinValue,MaxValue",
    # s1 – optional, nur falls du auch Header setzt:
    "optimization_categories.csv": "Rank,Name,Appearances",
    "scrum_steps.csv": "Step,Description,Interval,Result",
    "nlp_requirements.csv": "Keyword,Category,RelevantScrumEntities",
    "stress_pressure.csv": "Influence,AffectedEntities",  # tolerant
}

# Erlaube leichte Abweichungen (Spaces)
def _normalize_header(line: str) -> str:
    return ",".join([c.strip() for c in line.strip().split(",")])

# ```lang\n....```  -> liefert (lang, code)
CODEBLOCK_RE = re.compile(r"```([a-zA-Z0-9_\-+]*)\n(.*?)```", re.DOTALL)

def extract_code_blocks_with_lang(text: str) -> List[Tuple[str, str]]:
    if not text:
        return []
    blocks = []
    for m in CODEBLOCK_RE.finditer(text):
        lang = (m.group(1) or "").strip().lower()
        code = m.group(2).strip()
        blocks.append((lang, code))
    return blocks

def parse_stream_text(jsonl: str) -> str:
    """Fügt Ollama-/api/generate JSONL-Stream (response-Felder) zu einem Text zusammen."""
    out = []
    for line in jsonl.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            out.append(obj.get("response", ""))
        except Exception:
            out.append(line)
    return "".join(out)

def load_assistant_payloads(chat_json: Path) -> List[str]:
    """Holt alle Assistant-Antworten als Plaintext aus chat_*.json."""
    try:
        data = json.loads(chat_json.read_text(encoding="utf-8"))
    except Exception:
        return []

    payloads: List[str] = []
    if isinstance(data, dict) and isinstance(data.get("chat"), list):
        for msg in data["chat"]:
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            c = msg.get("content")
            if isinstance(c, str):
                payloads.append(c)
            elif isinstance(c, dict):
                if isinstance(c.get("text"), str):
                    payloads.append(parse_stream_text(c["text"]))
                elif isinstance(c.get("response"), str):
                    payloads.append(c["response"])
    return payloads

def find_chat_files(folder: Path) -> List[Path]:
    files = sorted(folder.glob("chat_*.json"))
    if files:
        return files
    legacy = folder / "chat.json"
    return [legacy] if legacy.exists() else []

def strategy_kind(strategy_name: str) -> str:
    s = (strategy_name or "").lower()
    if s.startswith("s1") or s.startswith("strategy1"):
        return "s1"
    return "s23"  # s2/s3 gleich behandelt

# ---------- Klassifizierung von Blöcken -> Zieldatei ----------

def classify_block(lang: str, code: str, expected: List[str]) -> Optional[str]:
    """
    Ordnet einen Codeblock anhand Sprache + Header + Inhalt einem Zieldateinamen zu.
    Gibt den Dateinamen zurück oder None, wenn unklar.
    """
    low = code.lower()
    # Mermaid (.mmd)
    if ("domain_graph.mmd" in expected) and (lang == "mermaid" or "graph td" in low or "graph lr" in low):
        return "domain_graph.mmd"
    # LaTeX (.tex)
    if ("optimization_model.tex" in expected) and (lang in ("tex", "latex") or "\\documentclass" in code):
        return "optimization_model.tex"
    # CSVs
    if lang in ("csv", "") or "," in code:
        first_line = code.splitlines()[0] if code else ""
        norm = _normalize_header(first_line.lower())
        for fname in expected:
            header = CSV_HEADERS.get(fname)
            if not header:
                continue
            if norm == _normalize_header(header.lower()):
                return fname
    return None

def keyword_fallback(assistant_text: str, missing_targets: List[str], keyword_map: Dict[str, List[str]]) -> Optional[str]:
    """
    Falls Klassifizierung nicht greift: per Keywords im Fließtext prüfen.
    """
    lower = assistant_text.lower()
    for fname in list(missing_targets):
        kws = keyword_map.get(fname, [])
        if not kws:
            continue
        match_count = sum(1 for kw in kws if kw.lower() in lower)
        if match_count >= 2:
            return fname
    return None

# ---------- Haupt-Logik ----------

def process_strategy_version_folder(folder: Path, overwrite: bool = False):
    """
    Erwartet Pfad: .../<provider>/<model>/<size>/<sX>/<vY>/
    Schreibt erwartete Dateien, ohne vorhandene zu überschreiben (default).
    """
    chat_files = find_chat_files(folder)
    if not chat_files:
        return

    # Pfad-Metadaten
    parts = folder.parts
    try:
        strategy = parts[-2]   # sX
        version = parts[-1]    # vY
        model = parts[-4]
        size = parts[-3]
        provider = parts[-5]
        model_label = f"{provider}/{model}:{size}"
    except Exception:
        strategy = parts[-2] if len(parts) >= 2 else "s?"
        version = parts[-1] if len(parts) >= 1 else "v?"
        model_label = folder.as_posix()

    print(f"\n🔍 {model_label} | {strategy} | {version}")

    kind = strategy_kind(strategy)
    keyword_map = S1_FILES if kind == "s1" else S23_FILES
    expected = list(keyword_map.keys())

    # Welche fehlen?
    existing = [fn for fn in expected if (folder / fn).exists()]
    missing = [fn for fn in expected if fn not in existing]

    for fn in expected:
        print(f"[{'✓' if fn in existing else 'X'}] {fn}" + ("" if fn in existing else " – Generiere…"))
    if not missing:
        return

    # Chats durchgehen (älteste zuerst)
    for chat_json in sorted(chat_files):
        payloads = load_assistant_payloads(chat_json)
        for text in payloads:
            if not missing:
                break

            # 1) Alle Codeblöcke extrahieren und einzeln klassifizieren
            for lang, code in extract_code_blocks_with_lang(text):
                if not missing:
                    break
                target = classify_block(lang, code, missing)
                if target:
                    out_path = folder / target
                    if out_path.exists() and not overwrite:
                        missing.remove(target)
                        continue
                    out_path.write_text(code, encoding="utf-8")
                    print(f"    → geschrieben (lang={lang or 'plain'}): {target}")
                    if target in missing:
                        missing.remove(target)

            # 2) Fallback: Wenn noch was fehlt, versuche Keyword-Match gegen kompletten Text
            if missing:
                fname = keyword_fallback(text, missing, keyword_map)
                if fname:
                    # nimm den ersten Block aus dem Text
                    blocks = extract_code_blocks_with_lang(text)
                    if blocks:
                        _, code = blocks[0]
                        out_path = folder / fname
                        if not (out_path.exists() and not overwrite):
                            out_path.write_text(code, encoding="utf-8")
                            print(f"    → geschrieben (fallback): {fname}")
                        if fname in missing:
                            missing.remove(fname)

        if not missing:
            break

def walk_llm_tree(base_root: Path, include_remote: bool = True):
    providers = ["local-llm"] + (["remote-llms"] if include_remote else [])
    candidates: List[Path] = []

    for provider in providers:
        root = base_root / provider
        if not root.exists():
            continue
        for model_dir in [p for p in root.iterdir() if p.is_dir()]:
            for size_dir in [p for p in model_dir.iterdir() if p.is_dir()]:
                for strategy_dir in [p for p in size_dir.iterdir() if p.is_dir() and strategy_name_ok(p.name)]:
                    for version_dir in [p for p in strategy_dir.iterdir() if p.is_dir() and version_name_ok(p.name)]:
                        candidates.append(version_dir)

    if not candidates:
        print(f"[!] Keine s*/v* Verzeichnisse unter: {base_root}")
        return

    for folder in sorted(candidates):
        process_strategy_version_folder(folder, overwrite=False)

def strategy_name_ok(name: str) -> bool:
    return bool(re.fullmatch(r"s\d+", name.lower()) or re.fullmatch(r"strategy\d+", name.lower()))

def version_name_ok(name: str) -> bool:
    return bool(re.fullmatch(r"v\d+", name.lower()))

def main():
    script_dir = Path(__file__).resolve().parent
    llm_root = (script_dir / ".." / "large-language-models").resolve()
    env_llm_root = os.getenv("LLM_ROOT")
    if env_llm_root:
        llm_root = Path(env_llm_root).resolve()

    if not llm_root.exists():
        print(f"[!] Basisordner nicht gefunden: {llm_root}")
        return

    print(f"📂 LLM_ROOT: {llm_root}")
    walk_llm_tree(llm_root, include_remote=True)

if __name__ == "__main__":
    main()
