#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Run Prompt Pipeline (auto from folder structure)
================================================

- Erkennt automatisch alle <LLM_ROOT>/(local-llm|remote-llms)/<model>/<size> Verzeichnisse
- Strategien:
    * ohne --strategy: alle vorhandenen sX Ordner je Modell/Size werden gefahren
    * mit --strategy sN: nur diese Strategie; Ordner wird bei Bedarf angelegt
- Prompts aus: input/strategyX_prompts.md (unterstützt .csv / toleriert promts.csv)
  Formate:
    1. Klassisch: #### Prompt <nr>:
    2. Neu: Prompts durch '---' getrennt
- Versionierung: <strategy>/v1, v2, ... + timestamp im Dateinamen
- API-URL via --url oder ENV LLM_API_URL

ENV (.env im Repo-Root):
  LLM_ROOT=../large-language-models
  LLM_INPUT_ROOT=../input
  LLM_API_URL=http://localhost:11434/api/generate  (optional)
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import requests
from dotenv import load_dotenv

# Regex Helfer
SIZE_RE   = re.compile(r"^\d+(?:\.\d+)?[bB]$")
STRAT_RE  = re.compile(r"^s[0-9]+$", re.IGNORECASE)
VERS_RE   = re.compile(r"^v[0-9]+$", re.IGNORECASE)
PROMPT_HDR_RE = re.compile(r"^#{1,6}\s*Prompt\s*(\d+)\s*:", re.IGNORECASE)

# -------------------------
# Args / ENV
# -------------------------
def parse_args() -> argparse.Namespace:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Run prompt pipeline against an LLM API (auto discover models/strategies).")
    ap.add_argument("--url", default=os.getenv("LLM_API_URL"),
                    help="API Endpoint. Default aus ENV LLM_API_URL.")
    ap.add_argument("--strategy", default=None,
                    help="Nur diese Strategie (s0–s9) ausführen. Ohne Angabe: alle vorhandenen Strategien.")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="Sekunden Pause zwischen Requests.")
    ap.add_argument("--timeout", type=float, default=120.0,
                    help="HTTP Timeout in Sekunden.")
    ap.add_argument("--dump_raw", action="store_true",
                    help="Rohantworten zusätzlich speichern (Debug).")
    return ap.parse_args()

# -------------------------
# Discovery: Modelle/Größen
# -------------------------
def discover_model_size_dirs(llm_root: Path) -> List[Path]:
    targets: List[Path] = []
    for scope in ("local-llm", "remote-llms"):
        scope_dir = llm_root / scope
        if not scope_dir.exists():
            continue
        for model_dir in scope_dir.iterdir():
            if not model_dir.is_dir():
                continue
            for size_dir in model_dir.iterdir():
                if size_dir.is_dir() and SIZE_RE.fullmatch(size_dir.name):
                    targets.append(size_dir)
    return sorted(targets)

def parse_model_and_size(size_dir: Path) -> Tuple[str, str]:
    parts = size_dir.parts
    anchor = None
    for i, p in enumerate(parts):
        if p in ("local-llm", "remote-llms"):
            anchor = i
            break
    if anchor is None or anchor + 2 >= len(parts):
        raise SystemExit(f"❌ Ungültiger Modellpfad: {size_dir}")
    model = parts[anchor + 1]
    size  = parts[anchor + 2]
    if not SIZE_RE.fullmatch(size):
        raise SystemExit(f"❌ Size-Folder sieht nicht gültig aus: {size}")
    return model, size

# -------------------------
# Discovery: Strategien
# -------------------------
def discover_existing_strategies(size_dir: Path) -> List[str]:
    s = []
    for d in size_dir.iterdir():
        if d.is_dir() and STRAT_RE.fullmatch(d.name):
            s.append(d.name)
    return sorted(s, key=lambda x: int(x[1:]))

# -------------------------
# Prompts (.md / .csv)
# -------------------------
def load_prompts_any(input_root: Path, strategy: str) -> List[Tuple[str, str]]:
    md = input_root / f"strategy{strategy[1:]}_prompts.md"
    csv = input_root / f"strategy{strategy[1:]}_prompts.csv"
    csv_tol = input_root / f"strategy{strategy[1:]}_promts.csv"

    if md.exists():
        return load_prompts_md(md)
    if csv.exists():
        return load_prompts_csv(csv)
    if csv_tol.exists():
        print(f"⚠️  Using tolerated filename: {csv_tol.name}")
        return load_prompts_csv(csv_tol)
    raise SystemExit(f"❌ Prompt-Datei nicht gefunden: {md.name} / {csv.name} / {csv_tol.name}")

def load_prompts_md(path: Path) -> List[Tuple[str, str]]:
    text = path.read_text(encoding="utf-8").strip()

    # Versuch 1: klassisches #### Prompt <nr>: Format
    lines = text.splitlines()
    prompts: List[Tuple[str, str]] = []
    cur_id: Optional[str] = None
    buf: List[str] = []

    def flush():
        nonlocal cur_id, buf
        if cur_id is not None:
            txt = "\n".join(buf).strip()
            if txt:
                prompts.append((cur_id, txt))
        cur_id, buf = None, []

    for ln in lines:
        m = PROMPT_HDR_RE.match(ln.strip())
        if m:
            flush()
            cur_id = m.group(1)
            buf = []
        else:
            if cur_id is not None:
                buf.append(ln)
    flush()
    if prompts:
        return prompts

    # Versuch 2: neues '---'-getrenntes Format
    parts = [p.strip() for p in text.split("---") if p.strip()]
    if parts:
        return [(str(i), p) for i, p in enumerate(parts)]

    raise SystemExit(f"❌ Keine Prompts erkannt in {path.name} – weder Header- noch '---'-Format.")

def load_prompts_csv(path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = [h.lower() for h in (reader.fieldnames or [])]
        id_col  = "id" if "id" in headers else None
        txt_col = "text" if "text" in headers else ("prompt" if "prompt" in headers else None)
        if not txt_col:
            raise SystemExit("❌ CSV braucht Spalten 'id'+'text' oder 'Prompt'.")
        idx = 0
        for r in reader:
            rid = str(r.get(id_col, "")).strip() if id_col else str(idx)
            txt = str(r.get(txt_col, "")).strip()
            if txt:
                rows.append((rid, txt))
                idx += 1
    if not rows:
        raise SystemExit(f"❌ CSV {path} enthält keine nutzbaren Zeilen.")
    return rows

# -------------------------
# Versionierung / Pfade
# -------------------------
def pick_next_version_dir(size_dir: Path, strategy: str, create_if_missing: bool = False) -> Path:
    strat_dir = size_dir / strategy
    if not strat_dir.exists():
        if create_if_missing:
            strat_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise SystemExit(f"❌ Strategie-Ordner fehlt: {strat_dir}")
    versions = [d for d in strat_dir.iterdir() if d.is_dir() and VERS_RE.fullmatch(d.name)]
    next_v = f"v{(max([int(d.name[1:]) for d in versions]) + 1) if versions else 1}"
    out_dir = strat_dir / next_v
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def timestamp_suffix() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# -------------------------
# API Call
# -------------------------
def send_prompt(api_url: str, model_tag: str, prompt: str, timeout: float) -> Tuple[str, str, float]:
    payload = {"model": model_tag, "prompt": prompt, "stream": False}
    t0 = time.time()
    resp = requests.post(api_url, json=payload, timeout=timeout)
    dur = time.time() - t0
    resp.raise_for_status()
    data = resp.json()
    answer = (data.get("response") or data.get("text") or "").strip()
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    return answer, raw, dur

# -------------------------
# Chat-Export
# -------------------------
def build_chat_export(strategy: str, messages: List[Dict[str, str]]) -> List[Dict]:
    return [{
        "title": f"LLM Session ({strategy})",
        "chat": {
            "history": {"messages": {str(i): m for i, m in enumerate(messages)}}
        }
    }]

# -------------------------
# Single Strategy Runner
# -------------------------
def run_strategy_for_size_dir(api_url: str, size_dir: Path, strategy: str,
                              input_root: Path, sleep: float, timeout: float, dump_raw: bool,
                              create_strategy_if_missing: bool):
    model, size = parse_model_and_size(size_dir)
    model_tag = f"{model}:{size}"
    print(f"\n🧭 Modell: {model_tag} | Strategie: {strategy}")

    prompts = load_prompts_any(input_root, strategy)
    print(f"📝 {len(prompts)} Prompts geladen ({strategy})")

    out_dir = pick_next_version_dir(size_dir, strategy, create_if_missing=create_strategy_if_missing)
    ts = timestamp_suffix()
    chat_path  = out_dir / f"chat_{ts}.json"
    log_path   = out_dir / f"log_{ts}.jsonl"
    stats_path = out_dir / f"stats_{ts}.csv"
    print(f"🗂️  Ausgabe: {out_dir} (Timestamp: {ts})")

    messages: List[Dict[str, str]] = []
    stats_rows: List[Dict[str, object]] = []

    with open(log_path, "w", encoding="utf-8") as logf:
        for pid, prompt in prompts:
            print(f"  ➤ Prompt {pid} senden …")
            messages.append({"role": "user", "content": prompt})
            try:
                answer, raw_json, dur = send_prompt(api_url, model_tag, prompt, timeout)
            except Exception as e:
                answer, raw_json, dur = f"[Error: {e}]", f"{e}", 0.0
            messages.append({"role": "assistant", "content": answer})
            print(f"    ✓ Antwort ({round(dur,2)}s)")

            if dump_raw:
                (out_dir / f"raw_{pid}_{ts}.json").write_text(raw_json, encoding="utf-8")

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "id": pid,
                "prompt": prompt,
                "duration_sec": dur,
                "response_raw": raw_json
            }
            logf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            stats_rows.append({
                "id": pid,
                "duration_sec": round(dur, 3),
                "prompt_length": len(prompt),
                "response_length": len(answer)
            })

            if sleep > 0:
                time.sleep(sleep)

    chat_export = build_chat_export(strategy, messages)
    chat_path.write_text(json.dumps(chat_export, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Chat gespeichert: {chat_path}")

    import csv as _csv
    with open(stats_path, "w", newline="", encoding="utf-8") as csvout:
        if stats_rows:
            writer = _csv.DictWriter(csvout, fieldnames=stats_rows[0].keys())
            writer.writeheader()
            writer.writerows(stats_rows)
        else:
            csvout.write("id,duration_sec,prompt_length,response_length\n")
    print(f"📊 Statistik gespeichert: {stats_path}")

# -------------------------
# Main
# -------------------------
def main():
    args = parse_args()
    if not args.url:
        raise SystemExit("❌ Keine API-URL gesetzt. Nutze --url oder ENV LLM_API_URL.")

    llm_root = os.getenv("LLM_ROOT")
    input_root = os.getenv("LLM_INPUT_ROOT")
    if not llm_root or not input_root:
        raise SystemExit("❌ ENV LLM_ROOT oder LLM_INPUT_ROOT fehlt.")
    llm_root = Path(llm_root).resolve()
    input_root = Path(input_root).resolve()
    if not llm_root.exists():
        raise SystemExit(f"❌ LLM_ROOT existiert nicht: {llm_root}")
    if not input_root.exists():
        raise SystemExit(f"❌ LLM_INPUT_ROOT existiert nicht: {input_root}")

    size_dirs = discover_model_size_dirs(llm_root)
    if not size_dirs:
        raise SystemExit(f"⚠️ Keine Modelle/Größen unter {llm_root} gefunden.")
    print(f"🔎 Gefundene Modelle/Größen: {len(size_dirs)}")

    for size_dir in size_dirs:
        model, size = parse_model_and_size(size_dir)
        if args.strategy:
            strategy = args.strategy
            if not STRAT_RE.fullmatch(strategy):
                raise SystemExit(f"❌ Ungültige Strategie: {strategy}. Erwartet s0–s9.")
            run_strategy_for_size_dir(args.url, size_dir, strategy, input_root,
                                      sleep=args.sleep, timeout=args.timeout, dump_raw=args.dump_raw,
                                      create_strategy_if_missing=True)
        else:
            strategies = discover_existing_strategies(size_dir)
            if not strategies:
                print(f"⏭️  {model}:{size} – keine sX-Ordner vorhanden, überspringe.")
                continue
            print(f"\n📦 {model}:{size} – Strategien: {', '.join(strategies)}")
            for strategy in strategies:
                run_strategy_for_size_dir(args.url, size_dir, strategy, input_root,
                                          sleep=args.sleep, timeout=args.timeout, dump_raw=args.dump_raw,
                                          create_strategy_if_missing=False)

    print("\n✅ Pipeline abgeschlossen.")

if __name__ == "__main__":
    main()
