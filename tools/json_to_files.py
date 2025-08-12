#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# -------------------- Codeblock-Parser --------------------

CODE_BLOCK_RE = re.compile(r"```([a-zA-Z]*)\n(.*?)```", re.DOTALL)

def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """Gibt Liste aus (lang, code) zurück; lang ist lowercase ohne Backticks."""
    blocks = []
    for m in CODE_BLOCK_RE.finditer(text or ""):
        lang = (m.group(1) or "").strip().lower()
        code = (m.group(2) or "").strip()
        if code:
            blocks.append((lang, code))
    return blocks

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

# -------------------- Pfad-/Repo-Helfer --------------------

def find_upwards_for_dir(start: Path, dirname: str) -> Optional[Path]:
    """Laufe vom Start-Verzeichnis nach oben, bis ein Unterordner 'dirname' existiert."""
    cur = start.resolve()
    root = cur.anchor
    while True:
        candidate = cur / dirname
        if candidate.is_dir():
            return candidate
        if str(cur) == root:
            return None
        cur = cur.parent

def parse_context_from_path(chat_path: Path) -> Dict[str, str]:
    """
    Erwartete Struktur:
      .../large-language-models/local-llm/<model>/<size>/sX/vY/chat_*.json
    Liefert: model, size, strategy ('s1'), version ('v4'), run_dir (Ordner mit chat.json)
    """
    parts = chat_path.resolve().parts
    ctx = {"model":"", "size":"", "strategy":"", "version":"", "run_dir": str(chat_path.parent)}
    try:
        # Finde 'local-llm' und lese die nächsten 4 Segmente
        idx = parts.index("local-llm")
        ctx["model"] = parts[idx+1]
        ctx["size"] = parts[idx+2]
        ctx["strategy"] = parts[idx+3]  # z.B. 's1'
        ctx["version"] = parts[idx+4]   # z.B. 'v4'
    except (ValueError, IndexError):
        # Fallback: suche irgend ein Segment 's\d+'
        for p in parts:
            if re.fullmatch(r"s\d+", p):
                ctx["strategy"] = p
                break
    return ctx

# -------------------- Prompt-Segmentierung --------------------

def load_strategy_prompts_md(chat_path: Path, strategy: str) -> Tuple[List[str], Path]:
    """
    Findet den input/ Ordner und lädt strategy{X}_prompts.md.
    Splittet in Segmente anhand von Zeilen '---'.
    """
    input_dir = find_upwards_for_dir(chat_path.parent, "input")
    if not input_dir:
        raise FileNotFoundError(f"Kein 'input/' Ordner oberhalb von {chat_path}")
    num = re.sub(r"[^0-9]", "", strategy or "")
    if not num:
        raise ValueError(f"Ungültige Strategiebezeichnung: '{strategy}'")
    md_path = input_dir / f"strategy{num}_prompts.md"
    if not md_path.is_file():
        raise FileNotFoundError(f"Nicht gefunden: {md_path}")

    text = md_path.read_text(encoding="utf-8")
    # Segmente anhand von '---' (Zeile nur aus Bindestrichen) trennen
    segments = re.split(r"(?m)^\s*---\s*$", text)
    # trim
    segments = [seg.strip() for seg in segments if seg.strip()]
    return segments, md_path

# -------------------- Strategie-Output-Plan --------------------
# Für s1 mappen wir die *Prompt-Segment-Nummer* auf Ausgabedateien.
# Segment-Indizes beziehen sich auf die Reihenfolge nach Split:
# 0: Intro; 1: Opt.-Probleme; 2: Scrum; 3: NLP; 4: Stress;
# 5: Entities/Relationships (kein Output);
# 6: Goals/Conditions/DecisionVariables; 7: LaTeX; 8: Mermaid

STRATEGY_SEGMENT_OUTPUTS: Dict[str, Dict[int, List[str]]] = {
    "s1": {
        1: ["p1_optimization_problem.csv"],
        2: ["p2_development_scrum.csv"],
        3: ["p3_nlp_pequirements.csv"],
        4: ["p4_stress_pressure.csv"],
        # 5: no output
        6: ["Goals.csv", "Conditions.csv", "DecisionVariables.csv"],
        7: ["p9_optimization_problem.tex"],
        8: ["p10_graph.mmd"],
    },
    # "s2": { ... }  # bei Bedarf ergänzen
}

# Für die Dateitypen filtern wir passende Codeblöcke:
WANT_LANG_BY_SUFFIX = {
    ".csv": {"csv", ""},            # leere Sprache zulassen
    ".tex": {"tex", "latex", ""},   # LaTeX
    ".mmd": {"mermaid", "md", ""},  # Mermaid
}

def desired_blocks(blocks: List[Tuple[str,str]], outfile: str) -> List[Tuple[str,str]]:
    """Filtert Codeblöcke anhand der Zielsuffixe."""
    suf = "".join(Path(outfile).suffixes)
    want = WANT_LANG_BY_SUFFIX.get(suf, {""})
    chosen = [b for b in blocks if (b[0] in want)]
    return chosen if chosen else blocks  # Fallback: nimm alles, wenn kein Match

# -------------------- Kernlogik --------------------

def process_chat(chat_json: Path):
    ctx = parse_context_from_path(chat_json)
    strategy = ctx.get("strategy", "").lower()
    run_dir = Path(ctx["run_dir"])

    segments, md_path = load_strategy_prompts_md(chat_json, strategy)
    plan = STRATEGY_SEGMENT_OUTPUTS.get(strategy)
    if not plan:
        print(f"[!] Keine Output-Plan-Definition für Strategie '{strategy}'. Datei: {chat_json.name}")
        return

    data = json.loads(chat_json.read_text(encoding="utf-8"))
    msgs = data.get("chat")
    if not isinstance(msgs, list):
        print(f"[!] Unerwartetes JSON-Format (erwarte 'chat' als Liste): {chat_json}")
        return

    print(f"\n🔎 Datei: {chat_json.name}")
    print(f"    Model: {ctx.get('model','?')} | Size: {ctx.get('size','?')} | Strategy: {strategy} | Version: {ctx.get('version','?')}")
    print(f"    Prompts: {md_path}")

    # Mappe: Prompt-Text (Segment) -> Segment-Index
    seg_index_by_text = {norm(segments[i]): i for i in range(len(segments))}

    i = 0
    while i < len(msgs):
        msg = msgs[i]
        if msg.get("role") != "user":
            i += 1
            continue

        user_txt = norm(msg.get("content",""))
        # Finde den Segment-Index, dessen Text (normiert) als Substring im User-Text vorkommt oder umgekehrt
        matched_seg = None
        for seg_norm, seg_idx in seg_index_by_text.items():
            if not seg_norm:
                continue
            if seg_norm in user_txt or user_txt in seg_norm:
                matched_seg = seg_idx
                break

        if matched_seg is None:
            i += 1
            continue

        outfiles = plan.get(matched_seg)
        if not outfiles:
            # Dieses Segment erzeugt keinen Output (z. B. Entities/Relationships)
            i += 1
            continue

        # Nächste Assistant-Antwort suchen
        j = i + 1
        while j < len(msgs) and msgs[j].get("role") != "assistant":
            j += 1
        if j >= len(msgs):
            print(f"[X] Keine Assistant-Antwort für Segment {matched_seg} gefunden.")
            i += 1
            continue

        ass_text = msgs[j].get("content","")
        blocks = extract_code_blocks(ass_text)
        if not blocks:
            print(f"[X] Keine Codeblöcke in Assistant-Antwort (Seg {matched_seg}).")
            i = j + 1
            continue

        # Schreiben
        if len(outfiles) == 1:
            chosen = desired_blocks(blocks, outfiles[0])
            code = chosen[0][1]
            (run_dir / outfiles[0]).write_text(code, encoding="utf-8")
            print(f"[✓] {outfiles[0]} geschrieben ({len(code)} Zeichen)")

        else:
            # mehrere Dateien (Goals/Conditions/DecisionVariables) -> nimm die ersten N passenden Blöcke
            N = len(outfiles)
            # Sortiere Dateinamen nach ihrer Position im Assistant-Text (falls genannt), sonst in gegebener Reihenfolge
            text_lc = ass_text.lower()
            ordered = sorted(outfiles, key=lambda name: text_lc.find(name.lower()) if name.lower() in text_lc else 10**9)

            # Filtere passende Blöcke pro Ziel-Datei
            bi = 0
            for name in ordered:
                cand = desired_blocks(blocks, name)
                if not cand:
                    continue
                code = cand[min(bi, len(cand)-1)][1]
                (run_dir / name).write_text(code, encoding="utf-8")
                print(f"[✓] {name} geschrieben ({len(code)} Zeichen)")
                bi += 1
                if bi >= len(blocks):
                    break

        i = j + 1

# -------------------- Traversal --------------------

def walk_and_process(path: Path):
    if path.is_file() and path.name.startswith("chat") and path.suffix == ".json":
        process_chat(path)
        return
    # Falls Verzeichnis: alle chat*.json in Tiefe 1 (typisch) oder rekursiv
    for p in path.rglob("chat*.json"):
        process_chat(p)

# -------------------- main --------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Aufruf: python extract_from_chat.py <pfad zu chat_*.json oder wurzelordner>")
        sys.exit(1)
    base = Path(sys.argv[1]).resolve()
    walk_and_process(base)
