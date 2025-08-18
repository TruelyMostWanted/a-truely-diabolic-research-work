# tools/run_prompt_pipeline.py

import os
import sys
import json
import time
import argparse
import requests
import datetime as dt
from pathlib import Path
from dotenv import load_dotenv
import re
import csv

# -------------------------
# Load .env
# -------------------------
load_dotenv()

# -------------------------
# CLI Argumente
# -------------------------
parser = argparse.ArgumentParser(description="Run prompt pipeline for LLM testing (env-only).")
parser.add_argument("--strategy", type=str, help="Strategie: 's1', 's2' oder 'strategy1', 'strategy2'. Ohne Angabe werden alle Strategien gefunden.")
parser.add_argument("--url", type=str, help="API URL (z. B. http://localhost:11434/api/generate). Überschreibt .env.")
parser.add_argument("--api_key", type=str, help="API Key (optional). Überschreibt .env.")
parser.add_argument("--run", type=int, default=1, help="Wie oft jede Strategie durchlaufen werden soll (Default=1).")
args = parser.parse_args()

# -------------------------
# Basis-Pfade aus .env
# -------------------------
LLM_ROOT = Path(os.getenv("LLM_ROOT", "../large-language-models")).resolve()
LLM_INPUT_ROOT = Path(os.getenv("LLM_INPUT_ROOT", "../input")).resolve()

# Provider-Default, falls in LLM_MODELS kein Providerpfad steht
LLM_DEFAULT_PROVIDER = os.getenv("LLM_DEFAULT_PROVIDER", "local-llm").strip()

# Standard-Größenlogik
LLM_DEFAULT_SIZE = os.getenv("LLM_DEFAULT_SIZE", "latest").strip()
LLM_MODEL_SIZE_MAP = {}
_size_map_raw = os.getenv("LLM_MODEL_SIZE_MAP", "").strip()
if _size_map_raw:
    try:
        LLM_MODEL_SIZE_MAP = json.loads(_size_map_raw)
    except json.JSONDecodeError:
        print("⚠️  LLM_MODEL_SIZE_MAP ist kein gültiges JSON. Ignoriere diese Variable.")

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
def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def looks_like_size_tag(tag: str) -> bool:
    """'7b', '24b', '1.8b' etc."""
    return bool(re.fullmatch(r"\d+(\.\d+)?b", tag.lower()))

def normalize_size_dir(model: str, tag: str) -> str:
    """
    Bestimmt den Ordnernamen für die Größenebene.
    1) LLM_MODEL_SIZE_MAP[model]
    2) tag, falls wie Größe
    3) LLM_DEFAULT_SIZE (falls gesetzt)
    4) 'unknown-size'
    """
    if model in LLM_MODEL_SIZE_MAP and LLM_MODEL_SIZE_MAP[model]:
        return str(LLM_MODEL_SIZE_MAP[model]).strip()
    if tag and looks_like_size_tag(tag):
        return tag.strip()
    if LLM_DEFAULT_SIZE:
        return LLM_DEFAULT_SIZE
    return "unknown-size"

def parse_model_spec(spec: str):
    """
    Erwartete Form:
      - 'provider/model:tag'  (z. B. 'local-llm/mistral-small3.1:24b')
      - 'model:tag'           (ohne provider)
      - 'provider/model'      (ohne tag)
      - 'model'
    Rückgabe: (provider_path_parts:list[str], model:str, tag:str)
    """
    spec = spec.strip()
    if not spec:
        return [], "", ""
    # Split tag
    if ":" in spec:
        left, tag = spec.split(":", 1)
    else:
        left, tag = spec, ""
    # Split provider path vs model
    parts = [p for p in left.split("/") if p]
    if not parts:
        return [], "", tag
    model = parts[-1]
    provider_parts = parts[:-1]  # kann leer sein
    return provider_parts, model, tag

def build_base_path_from_spec(provider_parts, model, size_dir) -> Path:
    """
    Baut Pfad strikt unterhalb LLM_ROOT:
      LLM_ROOT / <provider_parts...> / <model> / <size_dir>
    Falls kein Provider angegeben -> nutze LLM_DEFAULT_PROVIDER.
    """
    p = LLM_ROOT
    if provider_parts:
        for part in provider_parts:
            p = p / part
    else:
        p = p / LLM_DEFAULT_PROVIDER
    p = p / model / size_dir
    return p

# --- Strategie-Namen & Prompt-Dateien ----------------------------------------

def normalize_strategy_names(s: str):
    """
    Nimmt 's2' ODER 'strategy2' entgegen und gibt zurück:
      folder_name = 's2'         (für Pfade)
      file_base   = 'strategy2'  (für Dateien im input/)
    """
    s = (s or "").strip().lower()
    m = re.fullmatch(r"(?:s|strategy)\s*(\d+)", s)
    if not m:
        return None, None
    num = m.group(1)
    return f"s{num}", f"strategy{num}"

def discover_strategies_from_input():
    """
    Sucht in input/ nach 'strategyX_prompts.(csv|md)' und liefert ['s1','s2',...]
    """
    found_nums = set()
    for path in LLM_INPUT_ROOT.glob("strategy*_prompts.*"):
        m = re.match(r"strategy(\d+)_prompts\.", path.name, re.IGNORECASE)
        if m:
            found_nums.add(m.group(1))
    return [f"s{n}" for n in sorted(found_nums, key=lambda x: int(x))]

def load_prompts(strategy_folder_name: str):
    """
    Lädt Prompts:
      - bevorzugt: strategyX_prompts.csv / .md (Repo-Konvention)
      - Fallback:  sX_prompts.csv / .md
    Trennlogik für .md: '---'
    Für .csv: nimmt Spalte 'prompt' (case-insensitive), sonst alle nicht-leeren Zellen.
    """
    _, file_base = normalize_strategy_names(strategy_folder_name)
    if not file_base:
        print(f"❌ Ungültiger Strategiename: {strategy_folder_name}")
        return []

    candidates = [
        LLM_INPUT_ROOT / f"{file_base}_prompts.csv",
        LLM_INPUT_ROOT / f"{file_base}_prompts.md",
        LLM_INPUT_ROOT / f"{strategy_folder_name}_prompts.csv",
        LLM_INPUT_ROOT / f"{strategy_folder_name}_prompts.md",
    ]

    chosen = next((c for c in candidates if c.exists()), None)
    if not chosen:
        print(f"❌ Prompt-Datei nicht gefunden: {candidates[0]} oder {candidates[1]}")
        return []

    if chosen.suffix.lower() == ".md":
        with open(chosen, "r", encoding="utf-8") as f:
            content = f.read()
        prompts = [p.strip() for p in content.split("---") if p.strip()]
        if not prompts:
            print(f"⚠️  {chosen} ist leer?")
        return prompts

    # CSV
    prompts = []
    with open(chosen, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        print(f"⚠️  {chosen} ist leer?")
        return []
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    prompt_col_idx = None
    for i, h in enumerate(header):
        if (h or "").strip().lower() == "prompt":
            prompt_col_idx = i
            break
    if prompt_col_idx is not None:
        for r in body:
            if prompt_col_idx < len(r):
                cell = (r[prompt_col_idx] or "").strip()
                if cell:
                    prompts.append(cell)
    else:
        for r in rows:
            for cell in r:
                cell = (cell or "").strip()
                if cell:
                    prompts.append(cell)
    return prompts

# --- API ----------------------------------------------------------------------

def send_prompt(prompt_text: str, model_id: str):
    """Sendet einen Prompt an die API und gibt die Antwort zurück."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    payload = {"model": model_id, "prompt": prompt_text}
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {"text": resp.text}
    except Exception as e:
        return {"error": str(e)}

# --- Ordner-Handling ----------------------------------------------------------

def ensure_strategy_version_dir(base_path: Path, strategy_folder_name: str) -> Path:
    """
    Sichert <base_path>/<strategy>/vN und gibt den zu schreibenden vX-Pfad zurück.
    - Wenn keine Version existiert -> v1
    - Wenn v1..vK existieren -> v(K+1)
    """
    strategy_path = base_path / strategy_folder_name
    strategy_path.mkdir(parents=True, exist_ok=True)

    versions = []
    for d in strategy_path.iterdir():
        if d.is_dir() and re.fullmatch(r"v\d+", d.name):
            try:
                versions.append(int(d.name[1:]))
            except ValueError:
                pass
    next_idx = (max(versions) + 1) if versions else 1
    version_path = strategy_path / f"v{next_idx}"
    version_path.mkdir(parents=True, exist_ok=True)
    return version_path

# --- Modelle ausschließlich aus .env ------------------------------------------

def get_models_from_env_strict():
    """
    Liest LLM_MODELS (Komma-getrennt), erlaubt optional Provider-Pfad:
      'local-llm/mistral-small3.1:24b, remote-llms/qwen:32b, llama4:latest'
    Gibt Liste: (base_path, model_name, size_dir, model_id) zurück.
    Bricht ab, wenn leer.
    """
    env_val = os.getenv("LLM_MODELS", "").strip()
    if not env_val:
        print("❌ LLM_MODELS ist nicht gesetzt oder leer. Bitte in .env definieren.")
        sys.exit(1)

    exclude = set()
    ex_val = os.getenv("LLM_MODELS_EXCLUDE", "").strip()
    if ex_val:
        exclude = {x.strip() for x in ex_val.split(",") if x.strip()}

    items = []
    for raw in env_val.split(","):
        spec = raw.strip()
        if not spec or spec in exclude:
            continue
        provider_parts, model, tag = parse_model_spec(spec)
        if not model:
            continue
        size_dir = normalize_size_dir(model, tag)
        api_tag = tag if tag else "latest"
        model_id = f"{model}:{api_tag}"
        base_path = build_base_path_from_spec(provider_parts, model, size_dir)
        items.append((base_path, model, size_dir, model_id))

    if not items:
        print("❌ Keine gültigen Modelle aus LLM_MODELS ermittelt (ggf. durch EXCLUDE herausgefiltert).")
        sys.exit(1)
    return items

# -------------------------
# Modelle bestimmen (ENV-ONLY)
# -------------------------
model_dirs = get_models_from_env_strict()

# Fehlende Basispfade (bis size-Ebene) anlegen
for base_path, model_name, size_dir, model_id in model_dirs:
    if not base_path.exists():
        print(f"📁 Erstelle fehlenden Pfad: {base_path}")
        base_path.mkdir(parents=True, exist_ok=True)

print(f"🔎 Modelle/Größen: {len(model_dirs)}")

# -------------------------
# Strategien ermitteln
# -------------------------
strategies_to_run = []
if args.strategy:
    folder_name, _ = normalize_strategy_names(args.strategy)
    if not folder_name:
        print(f"❌ Ungültiger --strategy Wert: {args.strategy}. Erwarte z. B. 's2' oder 'strategy2'.")
        sys.exit(1)
    strategies_to_run = [folder_name]
else:
    strategies_to_run = discover_strategies_from_input()
    if not strategies_to_run:
        print(f"❌ Keine Strategien gefunden in {LLM_INPUT_ROOT} (erwarte Dateien wie 'strategy2_prompts.csv').")
        sys.exit(1)

print(f"🧭 Strategien: {', '.join(strategies_to_run)}")

# -------------------------
# Pipeline
# -------------------------
for run_idx in range(1, args.run + 1):
    print(f"\n🔁 Run {run_idx}/{args.run}")

    for base_path, model_name, size_dir, model_id in model_dirs:
        for strategy_folder in strategies_to_run:
            print(f"\n🧭 Modell: {model_name}:{size_dir} (API: {model_id}) | Strategie: {strategy_folder}")

            prompts = load_prompts(strategy_folder)
            print(f"📝 {len(prompts)} Prompts geladen ({strategy_folder})")

            # Versionierten Ausgabepfad vorbereiten
            output_dir = ensure_strategy_version_dir(base_path, strategy_folder)
            timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
            print(f"🗂️  Ausgabe: {output_dir} (Timestamp: {timestamp})")

            chat_history = []
            stats = []

            for idx, prompt in enumerate(prompts):
                print(f"  ➤ Prompt {idx} an {model_id} …")
                start_time = time.time()
                result = send_prompt(prompt, model_id)
                elapsed = time.time() - start_time

                if "error" in result:
                    print(f"    ❌ Fehler: {result['error']}")
                else:
                    print(f"    ✓ Antwort ({elapsed:.2f}s)")

                chat_history.append({"role": "user", "content": prompt})
                chat_history.append({"role": "assistant", "content": result})
                stats.append({"prompt_index": idx, "time": elapsed, "error": result.get("error")})

            # Speichern
            chat_file = output_dir / f"chat_{timestamp}.json"
            stats_file = output_dir / f"stats_{timestamp}.csv"

            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model": model_name,
                    "size_dir": size_dir,
                    "model_id": model_id,
                    "strategy": strategy_folder,
                    "run_index": run_idx,
                    "timestamp": utc_now().isoformat(),
                    "chat": chat_history
                }, f, ensure_ascii=False, indent=2)

            with open(stats_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["prompt_index", "time", "error"])
                writer.writeheader()
                writer.writerows(stats)

            print(f"💾 Chat gespeichert: {chat_file}")
            print(f"📊 Statistik gespeichert: {stats_file}")

print("\n✅ Pipeline abgeschlossen.")
