import spacy
import json
import pandas as pd
from collections import Counter

# Lade deutsches spaCy-Modell
nlp = spacy.load("en_core_web_sm")

# === 1. Lade JSON-Datei ===
with open("chat-export-1754490122086.json", "r", encoding="utf-8") as f:
    chat_data = json.load(f)

texts = []
for entry in chat_data:
    if "chat" in entry and "history" in entry["chat"] and "messages" in entry["chat"]["history"]:
        messages = entry["chat"]["history"]["messages"]
        for msg in messages.values():
            if msg.get("role") in ["user", "assistant"]:
                texts.append(msg["content"])

# === 2. Analyse je Text ===
results = []
global_tokens = []
global_lemmas = []
global_pos = []
global_ents = []

for idx, text in enumerate(texts):
    doc = nlp(text)
    tokens = [token.text for token in doc if not token.is_punct]
    lemmas = [token.lemma_ for token in doc if not token.is_punct]
    pos = [token.pos_ for token in doc]
    ents = [(ent.text, ent.label_) for ent in doc.ents]
    satzanzahl = len(list(doc.sents))

    # Sammle für Gesamtstatistik
    global_tokens.extend(tokens)
    global_lemmas.extend(lemmas)
    global_pos.extend(pos)
    global_ents.extend([ent[1] for ent in ents])

    # Speichere pro Nachricht
    results.append({
        "Antwort_Index": idx + 1,
        "Text": text,
        "Anzahl_Wörter": len(tokens),
        "Anzahl_Sätze": satzanzahl,
        "Einzigartige_Lemmata": len(set(lemmas)),
        "Anzahl_Named_Entities": len(ents),
        "Häufigste_POS": Counter(pos).most_common(1)[0][0] if pos else None
    })

# === 3. Speichere CSV mit Nachricht-Statistiken ===
df = pd.DataFrame(results)
df.to_csv("sprachliche_merkmale_pro_nachricht.csv", index=False)

# === 4. Gesamtstatistik ===
gesamt_statistik = {
    "Gesamtanzahl_Nachrichten": len(texts),
    "Gesamtanzahl_Wörter": len(global_tokens),
    "Einzigartige_Wörter": len(set(global_tokens)),
    "Einzigartige_Lemmata": len(set(global_lemmas)),
    "Häufigste_Wörter": Counter(global_tokens).most_common(10),
    "Häufigste_Lemmata": Counter(global_lemmas).most_common(10),
    "Häufigste_POS": Counter(global_pos).most_common(5),
    "Named_Entity_Typen": Counter(global_ents).most_common(5)
}

with open("sprachstatistik_gesamt.json", "w", encoding="utf-8") as f:
    json.dump(gesamt_statistik, f, indent=2, ensure_ascii=False)

print("✅ Sprachliche Analyse abgeschlossen.")
print("→ sprachliche_merkmale_pro_nachricht.csv")
print("→ sprachstatistik_gesamt.json")
