import os
import sys
import json
import time
import argparse
import requests
import markdown
import datetime
from pathlib import Path
from dotenv import load_dotenv

# -------------------------
# Load .env
# -------------------------
load_dotenv()

# -------------------------
# CLI Argumente
# -------------------------
parser = argparse.ArgumentParser(description="Run prompt pipeline for LLM testing.")
parser.add_argument("--strategy", type=str, help="Strategie (z.B. s1, s2) – ohne Angabe werden alle Strategien ausgeführt.")
parser.add_argument("--url", type=str, help="API URL (z.B. http://localhost:11434/api/generate)")
parser.add_argument("--api_key", type=str, help="API Key für Authentifizierung (optional, kann auch als Umgebungsvariable gesetzt werden).")
parser.add_argument("--run", type=int, default=1, help="Wie oft die Strategie durchlaufen werden soll (Default=1).")
args = parser.parse_args()

# -------------------------
# Basis-Pfade aus .env
# -------------------------
LLM_ROOT = Path(os.getenv("LLM_ROOT", "../large-language-models")).resolve()
LLM_INPUT_ROOT = Path(os.getenv("LLM_INPUT_ROOT", "../input")).resolve()

# -------------------------
# URL und API Key
# -------------------------
API_URL = args.url or os.getenv("LLM_API_URL")
if not API_URL:
    print("❌ Keine API-URL angegeben. Nutze --url oder setze LLM_API_URL in .env")
    sys.exit(1)

API_KEY = args.api_key or os.getenv("LLM_API_KEY")

# -------------------------
# Hilfsfunktionen
# -------------------------
def load_prompts_from_md(strategy_file: Path):
    """Lädt Prompts aus einer .md-Datei, getrennt durch '---'."""
    if not strategy_file.exists():
        print(f"❌ Prompt-Datei nicht gefunden: {strategy_file}")
        return []
    with open(strategy_file, "r", encoding="utf-8") as f:
        content = f.read()
    prompts = [p.strip() for p in content.split("---") if p.strip()]
    return prompts

def send_prompt(prompt_text: str):
    """Sendet einen Prompt an die API und gibt die Antwort zurück."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        resp = requests.post(API_URL, headers=headers, json={"model": "default", "prompt": prompt_text})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_model_dirs():
    """Liest alle model/size-Verzeichnisse."""
    model_dirs = []
    for root, dirs, files in os.walk(LLM_ROOT):
        parts = Path(root).parts
        if len(parts) >= 2 and parts[-2] != "large-language-models":
            # erwartet: .../<modell>/<size>
            model = parts[-2]
            size = parts[-1]
            if not size.startswith("s") and not size.startswith("v"):  # Nur Größen-Ebene
                model_dirs.append((Path(root), model, size))
    return model_dirs

# -------------------------
# Pipeline
# -------------------------
model_dirs = get_model_dirs()
print(f"🔎 Gefundene Modelle/Größen: {len(model_dirs)}")

strategies_to_run = []
if args.strategy:
    strategies_to_run = [args.strategy]
else:
    # Alle strategyX_prompts.md im Input-Ordner finden
    for file in LLM_INPUT_ROOT.glob("strategy*_prompts.md"):
        strategies_to_run.append(file.stem.split("_")[0])

for run_idx in range(1, args.run + 1):
    print(f"\n🔁 Run {run_idx}/{args.run}")

    for model_path, model_name, size in model_dirs:
        for strategy in strategies_to_run:
            print(f"\n🧭 Modell: {model_name}:{size} | Strategie: {strategy}")

            strategy_file = LLM_INPUT_ROOT / f"strategy{strategy[1:]}_prompts.md"
            prompts = load_prompts_from_md(strategy_file)
            print(f"📝 {len(prompts)} Prompts geladen ({strategy})")

            # Nächste freie Versionsnummer finden
            strategy_path = model_path / strategy
            strategy_path.mkdir(parents=True, exist_ok=True)
            version_dirs = [d for d in strategy_path.iterdir() if d.is_dir() and d.name.startswith("v")]
            next_version = f"v{len(version_dirs)+1}"

            # Ausgabeordner
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_dir = strategy_path / next_version
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"🗂️  Ausgabe: {output_dir} (Timestamp: {timestamp})")

            chat_history = []
            stats = []

            for idx, prompt in enumerate(prompts):
                print(f"  ➤ Prompt {idx} senden …")
                start_time = time.time()
                result = send_prompt(prompt)
                elapsed = time.time() - start_time
                if "error" in result:
                    print(f"    ❌ Fehler: {result['error']}")
                else:
                    print(f"    ✓ Antwort ({elapsed:.2f}s)")

                chat_history.append({
                    "role": "user",
                    "content": prompt
                })
                chat_history.append({
                    "role": "assistant",
                    "content": result
                })
                stats.append({"prompt_index": idx, "time": elapsed, "error": result.get("error")})

            # Speichern
            chat_file = output_dir / f"chat_{timestamp}.json"
            stats_file = output_dir / f"stats_{timestamp}.csv"

            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model": model_name,
                    "size": size,
                    "strategy": strategy,
                    "version": next_version,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "chat": chat_history
                }, f, ensure_ascii=False, indent=2)

            import csv
            with open(stats_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["prompt_index", "time", "error"])
                writer.writeheader()
                writer.writerows(stats)

            print(f"💾 Chat gespeichert: {chat_file}")
            print(f"📊 Statistik gespeichert: {stats_file}")

print("\n✅ Pipeline abgeschlossen.")
import os
import sys
import json
import time
import argparse
import requests
import markdown
import datetime
from pathlib import Path
from dotenv import load_dotenv

# -------------------------
# Load .env
# -------------------------
load_dotenv()

# -------------------------
# CLI Argumente
# -------------------------
parser = argparse.ArgumentParser(description="Run prompt pipeline for LLM testing.")
parser.add_argument("--strategy", type=str, help="Strategie (z.B. s1, s2) – ohne Angabe werden alle Strategien ausgeführt.")
parser.add_argument("--url", type=str, help="API URL (z.B. http://localhost:11434/api/generate)")
parser.add_argument("--api_key", type=str, help="API Key für Authentifizierung (optional, kann auch als Umgebungsvariable gesetzt werden).")
parser.add_argument("--run", type=int, default=1, help="Wie oft die Strategie durchlaufen werden soll (Default=1).")
args = parser.parse_args()

# -------------------------
# Basis-Pfade aus .env
# -------------------------
LLM_ROOT = Path(os.getenv("LLM_ROOT", "../large-language-models")).resolve()
LLM_INPUT_ROOT = Path(os.getenv("LLM_INPUT_ROOT", "../input")).resolve()

# -------------------------
# URL und API Key
# -------------------------
API_URL = args.url or os.getenv("LLM_API_URL")
if not API_URL:
    print("❌ Keine API-URL angegeben. Nutze --url oder setze LLM_API_URL in .env")
    sys.exit(1)

API_KEY = args.api_key or os.getenv("LLM_API_KEY")

# -------------------------
# Hilfsfunktionen
# -------------------------
def load_prompts_from_md(strategy_file: Path):
    """Lädt Prompts aus einer .md-Datei, getrennt durch '---'."""
    if not strategy_file.exists():
        print(f"❌ Prompt-Datei nicht gefunden: {strategy_file}")
        return []
    with open(strategy_file, "r", encoding="utf-8") as f:
        content = f.read()
    prompts = [p.strip() for p in content.split("---") if p.strip()]
    return prompts

def send_prompt(prompt_text: str):
    """Sendet einen Prompt an die API und gibt die Antwort zurück."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        resp = requests.post(API_URL, headers=headers, json={"model": "default", "prompt": prompt_text})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_model_dirs():
    """Liest alle model/size-Verzeichnisse."""
    model_dirs = []
    for root, dirs, files in os.walk(LLM_ROOT):
        parts = Path(root).parts
        if len(parts) >= 2 and parts[-2] != "large-language-models":
            # erwartet: .../<modell>/<size>
            model = parts[-2]
            size = parts[-1]
            if not size.startswith("s") and not size.startswith("v"):  # Nur Größen-Ebene
                model_dirs.append((Path(root), model, size))
    return model_dirs

# -------------------------
# Pipeline
# -------------------------
model_dirs = get_model_dirs()
print(f"🔎 Gefundene Modelle/Größen: {len(model_dirs)}")

strategies_to_run = []
if args.strategy:
    strategies_to_run = [args.strategy]
else:
    # Alle strategyX_prompts.md im Input-Ordner finden
    for file in LLM_INPUT_ROOT.glob("strategy*_prompts.md"):
        strategies_to_run.append(file.stem.split("_")[0])

for run_idx in range(1, args.run + 1):
    print(f"\n🔁 Run {run_idx}/{args.run}")

    for model_path, model_name, size in model_dirs:
        for strategy in strategies_to_run:
            print(f"\n🧭 Modell: {model_name}:{size} | Strategie: {strategy}")

            strategy_file = LLM_INPUT_ROOT / f"{strategy}_prompts.md"
            prompts = load_prompts_from_md(strategy_file)
            print(f"📝 {len(prompts)} Prompts geladen ({strategy})")

            # Nächste freie Versionsnummer finden
            strategy_path = model_path / strategy
            strategy_path.mkdir(parents=True, exist_ok=True)
            version_dirs = [d for d in strategy_path.iterdir() if d.is_dir() and d.name.startswith("v")]
            next_version = f"v{len(version_dirs)+1}"

            # Ausgabeordner
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_dir = strategy_path / next_version
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"🗂️  Ausgabe: {output_dir} (Timestamp: {timestamp})")

            chat_history = []
            stats = []

            for idx, prompt in enumerate(prompts):
                print(f"  ➤ Prompt {idx} senden …")
                start_time = time.time()
                result = send_prompt(prompt)
                elapsed = time.time() - start_time
                if "error" in result:
                    print(f"    ❌ Fehler: {result['error']}")
                else:
                    print(f"    ✓ Antwort ({elapsed:.2f}s)")

                chat_history.append({
                    "role": "user",
                    "content": prompt
                })
                chat_history.append({
                    "role": "assistant",
                    "content": result
                })
                stats.append({"prompt_index": idx, "time": elapsed, "error": result.get("error")})

            # Speichern
            chat_file = output_dir / f"chat_{timestamp}.json"
            stats_file = output_dir / f"stats_{timestamp}.csv"

            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model": model_name,
                    "size": size,
                    "strategy": strategy,
                    "version": next_version,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "chat": chat_history
                }, f, ensure_ascii=False, indent=2)

            import csv
            with open(stats_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["prompt_index", "time", "error"])
                writer.writeheader()
                writer.writerows(stats)

            print(f"💾 Chat gespeichert: {chat_file}")
            print(f"📊 Statistik gespeichert: {stats_file}")

print("\n✅ Pipeline abgeschlossen.")
