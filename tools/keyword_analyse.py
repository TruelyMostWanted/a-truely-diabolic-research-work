import pandas as pd
import json
import re
import spacy
from collections import defaultdict, Counter

# === 1. Lade spaCy-Modell ===
nlp = spacy.load("de_core_news_sm")

# === 2. Lade Keyword-Liste ===
try:
    keywords_df = pd.read_csv("keyword_list.csv", sep=None, engine="python")
except Exception as e:
    raise Exception("Fehler beim Laden der Keyword-Datei: " + str(e))

if "Keyword" not in keywords_df.columns or "Kategorie" not in keywords_df.columns:
    raise KeyError("Die CSV-Datei muss Spalten 'Keyword' und 'Kategorie' enthalten.")

keywords_df.dropna(subset=["Keyword"], inplace=True)
keywords_df["Keyword"] = keywords_df["Keyword"].astype(str).str.strip().str.lower()

# Erzeuge kategoriebasiertes Dictionary
keyword_dict = defaultdict(list)
for _, row in keywords_df.iterrows():
    keyword_dict[row["Kategorie"]].append(row["Keyword"])

# === 3. Lade Chat-JSON ===
with open("chat-export-1754490122086.json", "r", encoding="utf-8") as f:
    chat_data = json.load(f)

# Modellnamen aus allen Chat-Einträgen extrahieren
modellnamen = []
texts = []
for entry in chat_data:
    try:
        modellnamen.append(entry["chat"]["modelName"])
    except KeyError:
        pass

    if "chat" in entry and "history" in entry["chat"] and "messages" in entry["chat"]["history"]:
        messages = entry["chat"]["history"]["messages"]
        for msg in messages.values():
            if msg.get("role") in ["user", "assistant"]:
                texts.append(msg["content"])

# Modellname bestimmen
MODELLNAME = modellnamen[0] if len(set(modellnamen)) == 1 else "gemischt"

# === 4. Analyse: Keyword-Treffer pro Text ===
results = []
keyword_counter = Counter()
all_keywords_set = set(kw.lower() for kw in keywords_df["Keyword"])

for idx, text in enumerate(texts):
    doc = nlp(text.lower())
    lemmas = [token.lemma_ for token in doc]
    joined_lemmas = " ".join(lemmas)

    entry_result = {"Antwort_Index": idx + 1, "Text": text}
    for category, keywords in keyword_dict.items():
        matches = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", joined_lemmas)]
        entry_result[category] = len(matches)

    # Für Top-Keyword-Zählung
    keyword_counter.update([lemma for lemma in lemmas if lemma in all_keywords_set])

    results.append(entry_result)

# === 5. CSV-Ausgabe ===
df_results = pd.DataFrame(results)
df_results.to_csv("keyword_treffer_detailliert.csv", index=False)

df_summary = df_results.drop(columns=["Text", "Antwort_Index"]).sum().sort_values(ascending=False).reset_index()
df_summary.columns = ["Kategorie", "Anzahl Treffer"]
df_summary.to_csv("keyword_statistik_kategorien.csv", index=False)

# === 6. JSON-Statistik ===
gesamt_antworten = len(df_results)
treffer_pro_kategorie = df_summary.set_index("Kategorie")["Anzahl Treffer"].to_dict()
gesamt_treffer = sum(treffer_pro_kategorie.values())
durchschnitt = round(gesamt_treffer / gesamt_antworten, 2) if gesamt_antworten else 0

top_keywords = [{"Keyword": k, "Treffer": v} for k, v in keyword_counter.most_common(10)]

statistik = {
    "Modell": MODELLNAME,
    "Anzahl_Antworten": gesamt_antworten,
    "Gesamte_Treffer": int(gesamt_treffer),
    "Durchschnitt_Treffer_pro_Antwort": durchschnitt,
    "Treffer_Pro_Kategorie": {k: int(v) for k, v in treffer_pro_kategorie.items()},
    "Top_10_Keywords": top_keywords
}

with open("llm_keyword_statistik.json", "w", encoding="utf-8") as f:
    json.dump(statistik, f, indent=2, ensure_ascii=False)

print("✅ Analyse abgeschlossen.")
print("→ keyword_treffer_detailliert.csv")
print("→ keyword_statistik_kategorien.csv")
print("→ llm_keyword_statistik.json")
