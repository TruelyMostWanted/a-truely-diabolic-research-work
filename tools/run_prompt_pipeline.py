import os
import sys
import re
import json
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

# =========================
# .env laden
# =========================
load_dotenv()

# =========================
# CLI Argumente
# =========================
parser = argparse.ArgumentParser(description="Run prompt pipeline for local Ollama models.")
parser.add_argument("--strategy", type=str,
                    help="Strategie (z.B. s1, s2). Ohne Angabe werden alle Strategien aus input/ ausgeführt.")
parser.add_argument("--url", type=str, help="Ollama API URL, z.B. http://localhost:11434/api/generate")
parser.add_argument("--api_key", type=str, help="API Key (für Ollama nicht nötig; optional).")
parser.add_argument("--run", type=int, default=1, help="Wieviele Wiederholungen pro Strategie (Default=1).")
args = parser.parse_args()

# =========================
# Pfade aus .env
# =========================
LLM_ROOT = Path(os.getenv("LLM_ROOT", "../large-language-models")).resolve()
LLM_INPUT_ROOT = Path(os.getenv("LLM_INPUT_ROOT", "../input")).resolve()

# =========================
# API Konfiguration
# =========================
API_URL = args.url or os.getenv("LLM_API_URL")
if not API_URL:
    print("❌ Keine API-URL angegeben. Nutze --url oder setze LLM_API_URL in .env")
    sys.exit(1)
API_KEY = args.api_key or os.getenv("LLM_API_KEY")  # i. d. R. nicht nötig für Ollama

# =========================
# Utils
# =========================
SIZE_REGEX = re.compile(r"^\d+(?:\.\d+)?b$", re.IGNORECASE)  # 8b, 24b, 7.2b, 14b, ...
EXCLUDE_TOP = {"analyse", "remote-llms"}  # oberste Ordner, die wir ignorieren

def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def load_prompts_from_md(strategy_file: Path):
    """Lädt Prompts aus einer .md-Datei, getrennt durch '---'."""
    if not strategy_file.exists():
        print(f"❌ Prompt-Datei nicht gefunden: {strategy_file}")
        return []
    content = strategy_file.read_text(encoding="utf-8")
    return [p.strip() for p in content.split("---") if p.strip()]

def discover_local_ollama_models(llm_root: Path):
    """
    Erwartete Struktur:
      large-language-models/
        local-llm/
          <model>/
            <size>/            # size muss wie 8b/24b/7.2b aussehen
            sX/ vX/ ...        # werden ignoriert
    Rückgabe: Liste (size_dir_path, ollama_model, size, pretty)
    """
    results = []
    for top in llm_root.iterdir():
        if not top.is_dir():
            continue
        if top.name in EXCLUDE_TOP:
            continue
        if top.name != "local-llm":
            continue

        for model_dir in top.iterdir():
            if not model_dir.is_dir():
                continue
            model_name = model_dir.name

            for possible_size in model_dir.iterdir():
                if not possible_size.is_dir():
                    continue

                size_name = possible_size.name
                # Nur "echte" Größen wie 8b, 24b, 7.2b zulassen
                if not SIZE_REGEX.match(size_name):
                    # z. B. s1, v1, strategy0, etc. überspringen
                    continue

                # Jetzt sind wir bei .../local-llm/<model>/<size>
                ollama_model = f"{model_name}:{size_name}"
                pretty = f"{model_name}:{size_name}"
                results.append((possible_size, ollama_model, size_name, pretty))

    return results

def send_prompt_ollama(prompt_text: str, ollama_model: str, api_url: str):
    """Sendet Prompt an Ollama /api/generate und gibt die Text-Antwort zurück (oder dict mit 'error')."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"  # von Ollama i. d. R. ignoriert

    payload = {
        "model": ollama_model,
        "prompt": prompt_text,
        "stream": False
    }
    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=1800)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except requests.RequestException as e:
        return {"error": str(e)}

def next_version_dir(strategy_dir: Path) -> Path:
    """Ermittelt die nächste 'vX'-Version als Ordner."""
    strategy_dir.mkdir(parents=True, exist_ok=True)
    versions = [d for d in strategy_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
    next_v = f"v{len(versions) + 1}"
    out = strategy_dir / next_v
    out.mkdir(parents=True, exist_ok=True)
    return out

# =========================
# Modelle finden (nur local-llm/<model>/<size>)
# =========================
model_entries = discover_local_ollama_models(LLM_ROOT)
print(f"🔎 Gefundene lokale Ollama-Modelle: {len(model_entries)}")

# Strategien bestimmen
if args.strategy:
    strategies_to_run = [args.strategy]
else:
    # alle strategyX_prompts.md im input/ finden → sX-Liste
    s_list = []
    for p in LLM_INPUT_ROOT.glob("strategy*_prompts.md"):
        num = p.stem.replace("strategy", "").replace("_prompts", "")
        if num.isdigit():
            s_list.append(f"s{num}")
    strategies_to_run = sorted(set(s_list))

for run_idx in range(1, args.run + 1):
    print(f"\n🔁 Run {run_idx}/{args.run}")

    for size_dir, ollama_model, size, pretty in model_entries:
        for strategy in strategies_to_run:
            print(f"\n🧭 Modell: {pretty} | Strategie: {strategy}")

            # s2 → strategy2_prompts.md
            strategy_file = LLM_INPUT_ROOT / f"strategy{strategy[1:]}_prompts.md"
            prompts = load_prompts_from_md(strategy_file)
            print(f"📝 {len(prompts)} Prompts geladen ({strategy})")

            # Ziel: .../<model>/<size>/<strategy>/vX/
            strategy_path = size_dir / strategy
            out_dir = next_version_dir(strategy_path)

            ts = utc_stamp()
            print(f"🗂️  Ausgabe: {out_dir} (Timestamp: {ts})")

            chat_history = []
            stats_rows = []

            for idx, prompt in enumerate(prompts):
                print(f"  ➤ Prompt {idx} senden …")
                t0 = time.time()
                result = send_prompt_ollama(prompt, ollama_model, API_URL)
                elapsed = time.time() - t0

                if isinstance(result, dict) and "error" in result:
                    print(f"    ❌ Fehler: {result['error']}")
                    answer_text = ""
                    err_text = result["error"]
                else:
                    print(f"    ✓ Antwort ({elapsed:.2f}s)")
                    answer_text = result
                    err_text = ""

                chat_history.append({"role": "user", "content": prompt})
                chat_history.append({"role": "assistant", "content": answer_text})
                stats_rows.append({"prompt_index": idx, "time": round(elapsed, 3), "error": err_text})

            # Dateien speichern
            chat_file = out_dir / f"chat_{ts}.json"
            stats_file = out_dir / f"stats_{ts}.csv"

            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model": ollama_model.split(":")[0],
                    "size": size,
                    "strategy": strategy,
                    "version_dir": out_dir.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "chat": chat_history
                }, f, ensure_ascii=False, indent=2)

            import csv
            with open(stats_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["prompt_index", "time", "error"])
                writer.writeheader()
                writer.writerows(stats_rows)

            print(f"💾 Chat gespeichert: {chat_file}")
            print(f"📊 Statistik gespeichert: {stats_file}")

print("\n✅ Pipeline abgeschlossen.")
