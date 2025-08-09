# a-truely-diabolic-research-work
University Project / FoPra

# Naming-Convention

## Folder Structure
local-llms/gemma3/27b/s1/v1
remote-llms/chatgpt/4o/s1/v1

## Local-LLMs 
The chat history will always be named: 
chat.json

## Strategy 1 (s1): 10-Prompt Input
All output files of the LLMs are named as follow:
- p1_optimization_problem.csv
- p2_development_scrum.csv
- p3_nlp_pequirements.csv
- p4_stress_pressure.csv
- p6_goals_and_conditions.csv
- p7_decision_vairables.csv
- p9_optimization_problem.tex
- p10_graph.mmd

## Strategy 2: 3-Prompt Input
All output files of the LLMs are named as follows:
- p1.1_goals.csv
- p1.2_conditions.csv
- p1.3_decision_variables.csv
- p2_optimization_model.tex
- p3_graph.mmd


# LLM Keyword Analyse & Vergleich

Dieses Repository enthält Tools zur **automatisierten Auswertung** von Chat-Verläufen verschiedener LLMs
hinsichtlich ihrer **Keyword-Abdeckung** und **Prompt-Performance**.

---

## Ordnerstruktur

```
a-truely-diabolic-research-work/
│
├── large-language-models/         # Enthält alle LLM-Ergebnisse (local & cloud)
│   ├── local-llm/
│   │   └── MODEL_NAME/SIZE/sX/vY/ # Struktur: Modell / Parameter / Strategie / Version
│   │       └── chat.json          # Original-Chatverlauf
│   │       └── analyse_per_message.csv
│   │       └── analyse_summary.json
│   └── analyse/
│       └── global_comparison/     # Globale Vergleichsauswertungen (erstellt durch compare_models.py)
│
├── input/
│   ├── keyword_list.csv           # Referenzliste der Literatur-Keywords
│   ├── strategy1_prompts.csv      # Referenz-Prompts für Strategie s1
│   ├── strategy2_prompts.csv      # ...
│
├── tools/
│   ├── keyword_analyse.py         # Hauptskript zur Analyse eines gesamten LLM-Bestands
│   ├── compare_models.py          # Skript zum Vergleich aller Modelle & Diagrammerstellung
│
└── .env                           # ENV-Variablen (Pfade, Modelleinstellungen)
```

---

## Funktionsweise

### `keyword_analyse.py`
- **Liest** alle `chat.json`-Dateien unter `LLM_ROOT`
- Erkennt Modellname, Strategie (`sX`) und Version (`vY`) automatisch aus der Ordnerstruktur
- **Normalisiert** Nachrichten anhand der Referenz-Prompts (`strategyX_prompts.csv`)
- **Extrahiert** Keywords mit **spaCy** (Nomen, Eigennamen, wichtige Entitäten)
- **Vergleicht** Treffer mit der Referenzliste (`keyword_list.csv`)
- Berechnet **Precision**, **Recall** und **F1-Score** für:
  - jede einzelne Nachricht → `analyse_per_message.csv`
  - den gesamten Chat → `analyse_summary.json`
- Speichert pro Chat:
  - `analyse_per_message.csv` → detaillierte Trefferliste pro Nachricht
  - `analyse_summary.json` → Gesamtmetrik + Liste gefundener Keywords

**Konsolen-Output-Beispiel:**
```
Model: dolphin3-8b | Strategie: s1 | Version: v1
  chat.json found
  Normalizing to strategy prompts...
  Finished ✅
```

---

### `compare_models.py`
- Liest **alle** `analyse_summary.json` & `analyse_per_message.csv` aus
- Erstellt **globale Vergleichsmetriken**
- Speichert in `large-language-models/analyse/global_comparison/`:
  - `models_sorted.csv` → Modelle nach F1 sortiert
  - `topN_f1.png` → Balkendiagramm der Top-N Modelle
  - `keyword_heatmap.png` → Heatmap der Keyword-Abdeckung (1 = Keyword mindestens 1× gefunden)
  - `prompt_performance_MODEL.png` → Prompt-Performance je Modell
  - `prompt_performance.png` → **Alle Modelle in einem Diagramm**
  - `keyword_top5.csv` → Top-5 Keywords pro Modell

---

## Beispiel-Outputs

### **analyse_summary.json**
```json
{
  "ModelKey": "dolphin3-8b-s1-v1",
  "messages": 22,
  "TP": 62,
  "FP": 1258,
  "FN": 5108,
  "precision": 0.0469,
  "recall": 0.0120,
  "f1": 0.0191,
  "all_matched_keywords": ["scrum", "feature", "stakeholder", "..."],
  "matched_keyword_counts": [
    {"keyword": "scrum", "count": 11},
    {"keyword": "feature", "count": 7}
  ]
}
```

### **analyse_per_message.csv**
| ModelKey           | MessageIndex | Matched_Keywords          | Precision | Recall | F1   |
|--------------------|--------------|---------------------------|-----------|--------|------|
| dolphin3-8b-s1-v1  | 1            | scrum, stakeholder        | 0.50      | 0.10   | 0.17 |
| dolphin3-8b-s1-v1  | 2            | feature                   | 0.33      | 0.05   | 0.09 |

---

## Interpretation der Metriken
- **Precision** → Anteil gefundener Keywords, die korrekt waren (FP niedrig halten)
- **Recall** → Anteil der tatsächlich vorkommenden Keywords, die gefunden wurden (FN niedrig halten)
- **F1** → Harmonie zwischen Precision & Recall (0 = schlecht, 1 = perfekt)
- **TP** = True Positives → korrekte Keyword-Treffer  
- **FP** = False Positives → falsch-positive Treffer (nicht in Referenzliste)  
- **FN** = False Negatives → Keywords, die hätten gefunden werden müssen, aber fehlen  

---

## Nutzung

### ENV konfigurieren (`.env`)
```env
LLM_ROOT=../large-language-models
LLM_KEYWORDS=../input/keyword_list.csv
LLM_INPUT_ROOT=../input
LLM_SPACY_MODEL=en_core_web_sm
LLM_BATCH=64
```

### Hauptanalyse starten
```bash
cd tools
python keyword_analyse.py
```

### Vergleich starten
```bash
cd tools
python compare_models.py
```

---

## Tipps
- **Normalisierung** mit Strategie-Prompts ist entscheidend, um faire Vergleiche zu machen
- Diagramme sind besonders hilfreich, um Ausreißer zu erkennen
- Keyword-Heatmap zeigt sofort, welche Modelle welche Konzepte komplett verpassen
- Prompt-Performance-Grafiken helfen, Strategien gezielt zu verbessern

---
