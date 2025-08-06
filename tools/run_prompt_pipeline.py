import csv
import json
import time
import requests
import sys
from pathlib import Path
from datetime import datetime

# === Konfiguration ===
MODEL = "dolphin3:8b"
API_URL = "http://localhost:11434/api/generate"

# === API-Anfrage senden ===
def send_prompt(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        start = time.time()
        response = requests.post(API_URL, json=payload)
        duration = time.time() - start

        response.raise_for_status()
        result = response.json()

        raw = json.dumps(result, indent=2, ensure_ascii=False)
        answer = result.get("response", "").strip()
        return answer, raw, duration
    except Exception as e:
        return "[Error: no response]", str(e), 0

# === Hauptlogik ===
def main():
    strategy = sys.argv[1] if len(sys.argv) > 1 else "s1"
    input_file = f"{strategy}-prompts.csv"
    output_json = f"{strategy}-chat.json"
    output_log = f"{strategy}-log.jsonl"
    output_csv = f"{strategy}-stats.csv"

    if not Path(input_file).exists():
        print(f"[!] Eingabedatei nicht gefunden: {input_file}")
        return

    messages = []
    stats = []

    with open(input_file, newline='', encoding="utf-8") as csvfile, \
         open(output_log, "w", encoding="utf-8") as logf:

        reader = csv.DictReader(csvfile)
        for row in reader:
            prompt_id = row["id"]
            prompt = row["text"]

            print(f"🟡 Sende Prompt: {prompt_id}")
            messages.append({"role": "user", "content": prompt})

            answer, raw_response, duration = send_prompt(prompt)

            messages.append({"role": "assistant", "content": answer})
            print(f"🟢 Antwort erhalten für {prompt_id} ({round(duration,2)}s)")

            # Logging in .jsonl (für Debugging & Nachvollziehbarkeit)
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "id": prompt_id,
                "prompt": prompt,
                "duration_sec": duration,
                "response_raw": raw_response
            }
            logf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            # Für Statistik
            stats.append({
                "id": prompt_id,
                "duration_sec": round(duration, 2),
                "prompt_length": len(prompt),
                "response_length": len(answer)
            })

            time.sleep(1)

    # Export der Konversation
    chat_export = [{
        "title": f"LLM Session ({strategy})",
        "chat": {
            "history": {
                "messages": {
                    str(i): m for i, m in enumerate(messages)
                }
            }
        }
    }]

    with open(output_json, "w", encoding="utf-8") as out:
        json.dump(chat_export, out, indent=2, ensure_ascii=False)
        print(f"💾 Gespeichert: {output_json}")

    # Export der Statistik
    with open(output_csv, "w", newline='', encoding="utf-8") as csvout:
        writer = csv.DictWriter(csvout, fieldnames=stats[0].keys())
        writer.writeheader()
        writer.writerows(stats)
        print(f"📊 Statistik geschrieben in: {output_csv}")

if __name__ == "__main__":
    main()
