import sys
import json
import time
import requests
import argparse
import os

# --- API-Zugang ---
API_URL = "http://localhost:11434/api/chat"  # Ollama-kompatibel
API_KEY = None  # Optional

# --- Prompt-Datei einlesen (CSV oder Markdown mit "---" als Trenner) ---
def load_prompts(path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return [block.strip() for block in raw.split("---") if block.strip()]

# --- Chat-Historie mit Kontext senden ---
def send_prompt_with_context(messages: list[dict], model_id: str):
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    payload = {
        "model": model_id,
        "messages": messages
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {"text": resp.text}
    except Exception as e:
        return {"error": str(e)}

# --- JSON speichern ---
def save_output(path: str, history: list[dict], stats: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"chat": history, "stats": stats}, f, indent=2, ensure_ascii=False)

# --- Hauptfunktion ---
def main():
    parser = argparse.ArgumentParser(description="Prompt-Pipeline mit Kontextunterstützung für Ollama")
    parser.add_argument("model", help="Name des Ollama-Modells, z. B. llama3")
    parser.add_argument("--input", default="prompts.csv", help="Pfad zur Prompt-Datei (Standard: prompts.csv oder .md)")
    parser.add_argument("--output", default="chat_results.json", help="Ausgabedatei für Verlauf")
    args = parser.parse_args()

    model_id = args.model
    prompts = load_prompts(args.input)
    chat_history = []
    stats = []

    for idx, prompt in enumerate(prompts):
        print(f"  ➤ Prompt {idx + 1} an {model_id} …")

        # Neue Benutzernachricht anfügen
        current_history = chat_history + [{"role": "user", "content": prompt}]

        # Anfrage an das Modell mit Verlauf
        start_time = time.time()
        result = send_prompt_with_context(current_history, model_id)
        elapsed = time.time() - start_time

        if "error" in result:
            print(f"    ❌ Fehler: {result['error']}")
            chat_history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": ""}
            ])
        else:
            reply = result.get("message", {}).get("content", "") or result.get("text", "")
            print(f"    ✓ Antwort ({elapsed:.2f}s)")
            chat_history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": reply}
            ])

        stats.append({
            "prompt_index": idx,
            "time": elapsed,
            "error": result.get("error")
        })


    save_output(args.output, chat_history, stats)
    print(f"✔️  Fertig. Konversation gespeichert in {args.output}")

if __name__ == "__main__":
    main()
