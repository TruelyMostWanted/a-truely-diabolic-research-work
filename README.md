# a-truely-diabolic-research-work
University Project / FoPra

# Naming-Convention

## Folder Structure
local-llms/gemma3/27b/s1/v1
remote-llms/chatgpt/4o/s1/v1

## Local-LLMs 
The chat history will always be named: 
chat.json

## Strategy 1 (s1): 9-Prompts Input
All output files of the LLMs are named as follow:
- p0 **DOES NOT** generate any file(s)
- p1_optimization_problem.csv
- p2_development_scrum.csv
- p3_nlp_pequirements.csv
- p4_stress_pressure.csv
- p5 **DOES NOT** generate any file(s)
- p6.1_goals.csv
- p6.2_conditions.csv
- p6.3_decision_variables.csv
- p7_optimization_problem.tex
- p8_graph.mmd

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

###Manuelle Python Pipeline für LLM Tests Beispiele
```bash
python3 pipeline.py phi4:14b --input strategy1_prompts.md --output phi4:14b_s1.json
python3 pipeline.py phi4:14b --input strategy2_prompts.md --output phi4:14b_s2.json
python3 pipeline.py phi4:14b --input strategy3_prompts.md --output phi4:14b_s3.json

python3 pipeline.py dolphin3:8b --input strategy1_prompts.md --output dolphin3:8b_s1.json
python3 pipeline.py dolphin3:8b --input strategy2_prompts.md --output dolphin3:8b_s2.json
python3 pipeline.py dolphin3:8b --input strategy3_prompts.md --output dolphin3:8b_s3.json
```

###Auswertung Lokaler LLM
´´´txt


´´´
qwen32b:

Über alle drei Dateien hinweg fällt zuerst eine Terminologie-/Referenzinkonsistenz auf: In Relationships.csv wird die Entität Employee verwendet, während in Entities.csv Worker definiert ist. Das bricht die Referenzintegrität und kann jede nachgelagerte Auswertung kippen – hier ist eine konsequente Vereinheitlichung auf Worker nötig.

Daneben gibt es Schema- und Semantikfehler in den Optimierungsartefakten: In einer Variante sind die GoalType-Felder der Conditions.csv mit „–” statt min/max belegt (damit ist die Richtung der Restriktion unbestimmt), in einer anderen fehlen bei Goals.csv die verpflichtenden Präfixe maximize_/minimize_. Solche Abweichungen signalisieren, dass die CSVs zwar formal erstellt, die Regeldefinitionen aber nicht verlässlich angewandt wurden.

Deutlich ist auch das Muster falscher oder nicht existierender Attribut-/Entitätsverweise: Mehrfach werden Entitäten genutzt, die im Entity-Set gar nicht vorkommen (TeamMember, Budget, Resource, Compliance, Vendor), oder Attribute adressiert, die es in der jeweiligen Entität nicht gibt (z. B. Project.duration, Task.duration, Project.cost). Ebenso zeigt sich eine Aggregat-vs-Individuum-Verwechslung (Ziel auf Team.availability statt auf Worker.availability) und ein Verweis auf Sprint.duration, das in Sprint nicht definiert ist (Dauer müsste aus start_date/end_date abgeleitet oder als DV modelliert werden).

Schließlich treten Formatfehler in CSVs auf (mindestens ein DecisionVariables.csv mit uneinheitlicher Spaltenzahl), was die Parse-Stabilität bricht und jede automatisierte Pipeline stoppt.

Kurz: Trotz identischem Input variieren die Fehlerarten zwischen den Varianten, aber sie lassen sich auf vier Kernklassen reduzieren: (1) Terminologie/Referenzen (Employee↔Worker), (2) Schemaeinhaltung bei Goals/Conditions (Pflichtpräfixe, GoalType∈{min,max}, CriteriaType), (3) korrekte Zuordnung von Entitäten/Attributen (keine Phantom-Felder, Aggregat vs. Individuum), (4) strikt gültiges CSV-Format (konstante Spalten, korrekte DV-IDs/Domain-Notation). Eine robuste Auswertung erfordert, diese vier Punkte konsequent zu härten, unabhängig davon, ob mit 9-Shot, 3-Shot oder Single-Prompt generiert wurde.

deepseek-r1_8b:

In allen drei Dateien wird die vom Prompt geforderte Weiterverarbeitung gar nicht geliefert: Es fehlen die drei CSV-Blöcke (Goals/Conditions/DecisionVariables), ebenso LaTeX und Mermaid; stattdessen wird die Anweisung mehrfach wörtlich wiederholt, ohne Umsetzung. Das ist in s2 und s3 unmittelbar nach den Relationships zu sehen (die „Proceed and Create…“-Instruktion steht erneut im Text), aber es folgen keine gültigen CSV-Codeblöcke. Zudem schleichen sich teils lange Passagen irrelevanten „Word-Salads“/Gibberish ein (englisch/chinesisch gemischt), was auf massives Abschweifen hindeutet: s1 und s2 enthalten seitenlange, zusammenhangslose Mathematik-/Code-Fetzen; s3 ebenso. In den Relationships steckt ein systematischer Modellbruch: Es wird mehrfach „Employee“ referenziert, während die Entities „Worker (E2)“ definieren – ein Namens-Mismatch, der jede programmgesteuerte Verknüpfung zerreißt; zusätzlich wird „Sprint Review“ (mit Leerzeichen) verwendet, obwohl die Entity „SprintReview“ heißt. Dazu kommen formale CSV-Fehler/Trunkierungen: In s2 ist z.B. die Zeile R19 („refers_to_team“) abgeschnitten – das Gewicht fehlt hinter „1,1,“ – wodurch die CSV parserseitig ungültig wird; in s3 ist dieselbe Zeile vollständig, was die Läufe zusätzlich inkonsistent macht. Weiter problematisch: ungewöhnliche Attributnamen mit Sonderzeichen/Klammern („columns_(todo/done.)“) in den Entities, die spätere LaTeX/Mermaid/Parser-Pipelines leicht brechen können. 

deepseek-r1_32b:

Querschnittlich brechen alle drei Dateien die Referenzintegrität in Relationships.csv: Es wird „Employee“ benutzt, obwohl in Entities.csv „Worker“ definiert ist; außerdem steht „Sprint Review“ (mit Leerzeichen) statt SprintReview. In s1 tauchen fachfremde Domänenbegriffe (Product/Customer/Market/profit/cost/quality_rating) auf; Ziele und Bedingungen verweisen auf nicht definierte Entitäten/Attribute (z. B. Goals: Project.profit; Conditions: Budget.*), zudem nutzt Conditions nicht definierte „duration“-Felder (die Dauer müsste aus Datumsfeldern oder über eine DV abgeleitet werden). In s2 ist Conditions.csv semantisch leer definiert, weil GoalType nicht auf min/max gesetzt ist; zusätzlich werden „duration_(min)“-Attribute beim Sprint adressiert, die es dort nicht gibt, und die DecisionVariables.csv lässt sich wegen Spalten-Mismatch nicht robust parsen. In s3 werden in Goals Beziehungsnamen als Attribute verwendet (z. B. is_blocked_by), außerdem erneut falsche „duration_(min)“-Verweise bei Sprint in Goals/Conditions; DecisionVariables.csv ist auch hier parserseitig defekt (uneinheitliche Spaltenanzahl).

deepseek-r1_latest:

Übergreifend.
(1) Terminologie-/Dateninkonsistenzen bleiben unbereinigt: Die Relationen verwenden „Employee“ und „Sprint Review“, obwohl die Entitäten „Worker“ bzw. „SprintReview“ heißen; das wird in den Antworten teils einfach übernommen statt korrigiert (siehe die eingeblendeten Entitäten/Beziehungen in s3 und s2).

(2) Spezifikationsbruch bei der Pflichtausgabe: 3 CSV-Blöcke (je 10–15 Einträge) + LaTeX + Mermaid werden nicht konsistent geliefert. s1 driftet komplett in generische Business-Beispiele ab; s3 wiederholt vor allem die Aufgabenstellung/Grunddaten und liefert statt belastbarer Dateien ein Fragment/Template.

(3) Attribut- und Schemafehler: vielfach nicht existente Attribute (z. B. PredictedRevenuePerSprint, EffortPerTask, CompletionRateOfBacklog) und falsche Feldwerte (z. B. GoalType= maximize/minimize statt „max/min“, IsSum=TRUE statt „True/False“).

s1 (…_latest_s1.txt).
Die CSV-Beispiele basieren auf ausgedachten Domänen (Profit, Customer, Market etc.) und ignorieren die vorgegebenen SCRUM-Entitäten. Dazu kaputte Header/Inhalte: IDs klein geschrieben (g0), Felder mit Dollarzeichen, fehlende/verschobene Spalten, teils zusätzliche Spalten (Weight in DecisionVariables), insgesamt klar außerhalb des geforderten Schemas.

s2 (…_latest_s2.txt).
Zwar werden CSV-Blöcke produziert, aber mit massiven Schema-/Datenfehlern:
• Goals.csv: falsche GoalType-Werte („maximize/minimize“), zahlreiche nicht vorhandene Attribute/Entity-Namen (z. B. Project.PredictedRevenuePerSprint, Team.EffortPerTask, TMSSaturationLoss.RiskOfBlockedProgress).
• Conditions.csv: Zeilen formal defekt (fehlendes Komma in der ID-Spalte, eingeschobenes „C“ in IsSum, Tippfehler wie minimize/UserStory im GoalType-Feld); Attribute weichen von den Entitäten ab (Team.Size statt team_size, SprintReview.Attendees statt attendees_count, Fantasie-Attribute wie DailyDurationMin, BudgetExceedance).
• DecisionVariables.csv: geforderte MinValue/MaxValue fehlen (nur Bereich in Domain angegeben), damit spaltenweise unvollständig und nicht parsebar.

s3 (…_latest_s3.txt).
Statt konkreter, valider Dateien wird überwiegend die Aufgabenstellung/Datengrundlage wiedergegeben; es fehlen die drei geforderten 10–15-zeiligen CSVs. Zusätzlich enthält das LaTeX-Gerüst nicht standardisierte Pakete/Fragmente (z. B. \usepackage{relgraph}) und ist so nicht kompilierbar. Die Relationen werden mit den bereits erwähnten „Employee“/„Sprint Review“-Diskrepanzen zitiert, ohne Bereinigung.
Kurz: Alle drei Ausgaben verfehlen an verschiedenen Stellen die vorgegebene Struktur; Hauptprobleme sind Domänen-Drift (s1), massiv fehlerhafte Felder/Spalten (s2) sowie fehlende, valide Endergebnisse und nicht kompilierbares LaTeX (s3).

dolphin3_8b:

Querschnittlich: In den Relationships.csv wird „Employee“ statt der in Entities.csv definierten Entität „Worker“ verwendet sowie „Sprint Review“ (mit Leerzeichen) statt „SprintReview“ – Referenzbrüche, die jede automatische Verknüpfung kippen. s1: Goals/Conditions ignorieren das SCRUM-Domänenmodell und verweisen auf fachfremde Entitäten/Attribute (Company/Supplier/Customer/Logistics/Product); IsSum als 0/1 statt True/False; DecisionVariables mit falschem ID-Präfix (D… statt DV…), gemischten Intervall-Domains und widersprüchlichen Min/Max; LaTeX nur als Platzhalter, Mermaid nicht umgesetzt. s2: In Conditions.csv steht GoalType durchgängig auf „–“ statt min/max; es tauchen nicht existente Attribute (z. B. „skill level“ bei Team) und Format-/Tippfehler auf; DecisionVariables.csv ist schemawidrig (D… statt DV…, Domains als „60 to 240“/Datumsintervalle, teils fehlende Min/Max) und daher nicht robust parse-bar; LaTeX generisch, Mermaid mit Platzhalterdaten. s3: Goals/Conditions referenzieren Phantom-Felder/Aggregate, die im Modell nicht existieren (z. B. total_workers, project_end_date, features_delivered_per_sprint, average_availability, avg_story_points_completed_per_sprint); DecisionVariables mit denselben ID-/Domain-Problemen; LaTeX spiegelt nicht die tatsächlichen CSV-Inhalte (Indices als Meta-Felder), Mermaid vermischt Kantenbedeutungen/Farbstile ohne konsistente Knoten-Attribut-Anbindung. Zusammengefasst wiederholen sich vier Fehlerklassen: (1) Terminologie/Referenzen (Employee↔Worker, „Sprint Review“↔SprintReview), (2) CSV-Schema (ID-Präfixe, IsSum, GoalType, Domains/Min/Max), (3) Entitäts-/Attribut-Mapping (falsche/erfundene Felder), (4) Endartefakte (LaTeX/Mermaid als Platzhalter statt Nutzung der gelieferten CSVs).

gemma3_1b:

Querschnittlich: Die Modellbasis bleibt inkonsistent – in den Relationships wird „Employee“ und „Sprint Review“ verwendet, obwohl die Entities „Worker“ bzw. „SprintReview“ definieren; das bricht die Referenzintegrität und wird unverändert übernommen. :contentReference[oaicite:0]{index=0} s1: Es existiert kein gültiges Goals.csv; stattdessen eine „Goals.txt“-Liste mit zahlreichen Namen, die nicht mit maximize_/minimize_ beginnen (z. B. Increase_/Decrease_), also gegen die Namenskonvention verstoßen. Zudem ist Conditions.csv schematisch falsch (ID beginnt mit G…, Name=„Must_Match“, GoalType=„Login“ statt {min,max}, EntityName/EntityAttribute verweisen auf nicht vorhandene Domänenobjekte wie Login/Data/Source); DecisionVariables.csv enthält nur eine Ein-Zeilen-„Matrix“ der Tokens G001…G020 statt valider Spalten. :contentReference[oaicite:1]{index=1} :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3} s2: Goals.csv verletzt mehrfach die Spezifikation (Name nicht snake_case; GoalType mit „ProductRevenue“ statt {min,max}; EntityName/EntityAttribute keine gültigen Entities/Attribute). Conditions.csv hat die GoalType-Spalte mit Entitätsbezeichnungen gefüllt (z. B. FeatureDocumentation) und nutzt Entity-Namen als Attribute; DecisionVariables.csv nutzt D… statt DV… als ID-Präfix, „1“ als Datentyp und skalar/intervallartige Domains statt Mengen „{…}“. Das LaTeX ist Platzhalter-haft („Max_N …“) und entspricht nicht der geforderten 5-Abschnitt-Struktur. :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6} :contentReference[oaicite:7]{index=7} s3: Anstelle der geforderten fünf Artefakte (3×CSV, 1×LaTeX, 1×Mermaid) liefert der Output überwiegend Projekt-/Dateistruktur-Erklärungen; die eigentlichen Dateien/Diagramme fehlen bzw. bleiben generisch. :contentReference[oaicite:8]{index=8} :contentReference[oaicite:9]{index=9} :contentReference[oaicite:10]{index=10}


gemma3_27b:

gemma3-27b_s1: deutliche Domänen- und Formatabweichung; der Output “erfindet” ein generisches Business-Szenario (Product/Market/Inventory) und benutzt Platzhalter-Attribute (Attribute0–Attribute8) statt der geforderten SCRUM-Entitäten/Attribute – sogar explizit als Annahme deklariert; dadurch sind Ziele/Bedingungen und die folgenden Tabellen/LaTeX nicht mit deinem Datensatz kompatibel. Die LaTeX-Passagen modellieren eine allgemeine Ressourcen/Budget-Optimierung mit eigenen Variablen statt der geforderten Sets/Indices/Goals/Conditions aus den CSVs. 

gemma3-27b_s2: formal liefert es CSVs, aber mit mehreren inhaltlichen/typologischen Problemen: (a) Bedingungen operieren auf String-Feldern mit „min/max“ (z. B. Feature.status, Task.status, Worker.email, Team.team_status), was semantisch kein Ordnungsmaß hat; (b) Proxy-Maße sind fragwürdig (z. B. ProductBacklog.number_of_entries als „Priorisierung“; FeatureDocumentation.creation_date als „Qualität“); (c) in DecisionVariables werden String-Variablen mit numerischen Min/Max kombiniert (z. B. feature_priority/String mit MinValue = 1, MaxValue = 3), was die Typkonsistenz verletzt; (d) weitere Mischungen aus kategorischen Domains und numerischen Schranken wiederholen das Muster. 

gemma3-27b_s3: Ausgabe ist teils unvollständig/abgebrochen; die IDs der DecisionVariables verstoßen gegen die Namensregel (D0… statt DV0…); zudem wieder Typ/Range-Mischungen (z. B. feature_priority als String mit Min/Max=1–3; release_plan_date als String mit Min/Max Monats-Strings). Die LaTeX-Sektion verwendet generische Summen über Variablen (team_size_i, sprint_velocity_k) ohne saubere Rückbindung an die erzeugten CSV-IDs; die Mermaid-Grafik führt Entitäten ein, die außerhalb deiner Liste nicht belegt sind (z. B. „User“) und bleibt strukturell sehr dünn verbunden. 

llama3.3_latest:

llama3.3_latest_s1: liefert auf die Aufforderungen zu Goals/Conditions/DecisionVariables, LaTeX und Mermaid überhaupt keine Artefakte — die ASSISTANT-Blöcke bleiben leer; damit werden wesentliche Vorgaben (3×CSV je 10–15 Zeilen, LaTeX mit 5 Sektionen, Mermaid-Graph) komplett verfehlt. :contentReference[oaicite:0]{index=0}

llama3.3_latest_s2: gleiches Muster wie s1 — nach der detaillierten Aufgabenstellung folgen keine generierten CSV-Blöcke, kein LaTeX und kein Mermaid; die Spezifikation (IDs, snake_case, GoalType ∈ {min,max}, IsSum boolean etc.) wird dadurch gar nicht adressiert. :contentReference[oaicite:1]{index=1}

llama3.3_latest_s3: erneut keine nutzbaren Ergebnisse; trotz erneuter, vollständiger Anweisung bleibt der Output ohne die geforderten fünf Code-Blöcke (3×CSV, 1×.tex, 1×.mmd). Damit ist die Anforderung „alle zuvor bereitgestellten Daten verwenden“ ebenfalls nicht erfüllt. :contentReference[oaicite:2]{index=2}

mistral_latest:

mistral_latest_s1: liefert Domänen- und Formatbruch schon in den Beispiel-CSV—Goals/Conditions/DecisionVariables referenzieren fachfremde Objekte („Profit, Waste, Customer Satisfaction“) statt der SCRUM-Entitäten und sind syntaktisch kaputt (Punkte/Kommas im Fließtext statt Spalten; z. B. „Maximize profit … .False,max,…“); zudem falsche ID-Formate (G001/D001 statt G0…/DV…, DV-Präfix fehlt) und keine konsistenten 10–15 Zeilen pro Datei. :contentReference[oaicite:0]{index=0}

mistral_latest_s2: erzeugt zwar CSV-Blöcke, bricht aber mehrfach die Spezifikation: (i) in Goals/Conditions stehen **Ausdrücke** in `EntityAttribute` (z. B. `project_end - project_start`, `team_end - team_start`) statt echter Attributnamen; (ii) Groß-/Kleinschreibung und Bezeichner weichen vom Entity-Schema ab (z. B. `Budget`, `Team_size`, `End_date`); (iii) DecisionVariables: falsche IDs (D01… statt **DV…**), uneinheitliche/notationsfremde Domains (`{1, 2, . 15}`, `Inf`) sowie fehlerhafte Wertebereiche. 

mistral_latest_s3: wiederholte Schemafehler in allen Artefakten: (i) Goals/Conditions mit falscher Attributschreibweise und teils falschen Entitäten (z. B. `Budget`, `Project_end`, `Employee` in Conditions), (ii) DecisionVariables mit nicht geforderter Typ-/Domain-Notation (`Number`, `Percentage`, `[0, 100]`, `inf`) und fehlendem **DV**-Präfix, (iii) LaTeX- und Mermaid-Teile bleiben generisch bzw. losgelöst von den gelieferten CSVs; zusätzlich sind die eingebetteten Relationships weiterhin inkonsistent („Employee“ statt **Worker**, „Sprint Review“ statt **SprintReview**). 

mistral-small3.1_latest:

mistral-small3.1_latest_s1.txt: Reagiert so, als lägen Entities/Relations nicht vor, fordert sie erneut an und liefert danach nur generische Platzhalter statt der geforderten Artefakte; damit ignoriert es den eingebetteten Datensatz. :contentReference[oaicite:0]{index=0} Die erzeugte LaTeX-Struktur ist allgemein gehalten („generic structure“) und verweist nicht auf konkrete IDs/Attribute oder die 5-Abschnitt-Spezifikation; CSV-Dateien und Mermaid sind nicht erkennbar. :contentReference[oaicite:1]{index=1}

mistral-small3.1_latest_s2.txt: Erstellt Goals/Conditions/DecisionVariables, aber mit formalen Inkonsistenzen: In DecisionVariables fehlen z.B. bei String-Variablen die MaxValue-Spalte (DV11/DV12), wodurch die Spaltenanzahl uneinheitlich wird. :contentReference[oaicite:2]{index=2} Der anschließende LaTeX-Teil ist erneut generisch („Since I don't have the actual data…“) und widerspricht der Anweisung, alle erzeugten CSVs zu verwenden. :contentReference[oaicite:3]{index=3} Zudem übernimmt es offensichtliche Inkonsistenzen aus den Relations (z.B. „Employee“ vs. Entity „Worker“, „Sprint Review“ vs. „SprintReview“) ungeprüft weiter, was spätere Referenzen unstabil macht. :contentReference[oaicite:4]{index=4}

mistral-small3.1_latest_s3.txt: Artefakte deutlich korrupt: Ziel–Typ widerspricht sich („minimize_project_duration“ mit GoalType=max). :contentReference[oaicite:5]{index=5} Es werden nicht existierende Attribute verwendet (z.B. Sprint „duration“). :contentReference[oaicite:6]{index=6} Zusätzlich treten vermischte/duplizierte Header und zerrissene Zeilen in Goals/Conditions auf (u.a. falsche Felder im Conditions-Block, doppelte Blöcke), und der LaTeX-Teil enthält hineingestreute CSV-Fragmente. 


mistral-small3.2_24b:

Querschnittlich: die Referenzintegrität ist weiterhin gebrochen – in den Relationships steht „Employee“ und „Sprint Review“, während die Entitäten „Worker“ (E2) bzw. „SprintReview“ (E12) heißen; das wird in den Dateien unverändert übernommen. :contentReference[oaicite:0]{index=0}

mistral-small3.2_24b_s1.txt: liefert statt SCRUM-Formulierung ein generisches Netzwerkfluss-Modell in LaTeX (Knoten/Arkbögen N,A; Variablen x_ij, y_ij etc. mit „Flow Conservation“, „Capacity Constraints“), ohne Bezug auf die bereitgestellten Entities/Relations/CSV-Artefakte; die geforderten 3 CSV-Dateien (Goals/Conditions/DecisionVariables) fehlen. :contentReference[oaicite:1]{index=1}

mistral-small3.2_24b_s2.txt: (a) DecisionVariables.csv ist strukturell defekt: innerhalb des DV-Blocks stehen plötzlich komplette **Goals-Zeilen** (G11…G35), Datentyp/Domain/Min/Max sind inkonsistent (z. B. „Date“, „None“) und einzelne Zeilen sind unvollständig. :contentReference[oaicite:2]{index=2} (b) Conditions.csv enthält massenhaft Duplikate und nutzt falsche/unerlaubte Attributnamen (z. B. `Sprint.achievement` statt `achievement_of_goal`, `Stakeholder.engagement` existiert nicht). :contentReference[oaicite:3]{index=3}

mistral-small3.2_24b_s3.txt: Goals/Conditions missachten mehrere Konventionen: Zielnamen „minimize_*“ werden mit `GoalType=max` kombiniert; es werden **nicht vorhandene Attribute** verwendet (z. B. `Sprint.duration`), und die erzeugten CSV-Blöcke brechen bzw. bleiben fragmentarisch. Zudem liegt derselbe „Employee“/„Sprint Review“–Bruch in den Beziehungen zugrunde. :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5}

phi4_14b:

Querschnittlich: Die Referenzintegrität ist im Beziehungsmodell gebrochen – „Employee“ statt der in Entities definiertem „Worker“ sowie „Sprint Review“ (mit Leerzeichen) statt „SprintReview“. Das wird in den Dateien unverändert übernommen. :contentReference[oaicite:0]{index=0}

phi4_14b_s1.txt: Die drei geforderten CSVs ignorieren das SCRUM-Domänenmodell (Goals/Conditions/DecisionVariables referenzieren u. a. Company/Customer/Market) und verstoßen gegen mehrere Spezifikationen: Conditions mit `GoalType=NA` statt {min,max}, DecisionVariables mit falschem ID-Präfix (D… statt DV…) und ungeeigneter Domain-/Werte-Notation (z. B. Intervalle/∞ bzw. fehlende Felder bei Datum). LaTeX und Mermaid sind reine Platzhalter-Templates ohne Nutzung der erzeugten CSVs. :contentReference[oaicite:1]{index=1}

phi4_14b_s2.txt: CSVs greifen teils korrekte Entitäten auf, verweisen aber auf **nicht vorhandene Attribute** (z. B. `Sprint.duration_(min)` – das Feld existiert bei *SprintPlanning*, nicht bei *Sprint*). DecisionVariables enthalten formale Fehler (z. B. `sprint_start_date` ohne Domain/Min; Intervall-/Unendlichkeitsnotation `[0, ∞)` für `budget_allocation`). Auch hier bleiben LaTeX/Mermaid generische Platzhalter statt einer Modellableitung aus den CSVs. :contentReference[oaicite:2]{index=2}

phi4_14b_s3.txt: Die 5 Artefakte werden erzeugt, sind aber fachlich/strukturell inkonsistent: Goals/Conditions nutzen fragwürdige Proxy-Felder (z. B. `end_date` als „Sprint-Dauer“), DecisionVariables mischen Datums-/∞-Notation mit fehlenden Werten, der LaTeX-Teil referenziert Attribute fehlerhaft (z. B. `avg.__story__points`), und der Mermaid-Graph bleibt unvollständig/trunkiert. Die Beziehungsinkonsistenzen („Employee“, „Sprint Review“) bestehen fort. :contentReference[oaicite:3]{index=3}
---

Beispielzeiten der lokalen LLMs:

dolphin3_8b_s1.json: 157.225 s (≈ 0:02:37)
phi4_14b_s1.json: 1012.435 s (≈ 0:16:52)
qwen3_32b_s1.json: 8687.907 s (≈ 2:24:48)

## Tipps
- **Normalisierung** mit Strategie-Prompts ist entscheidend, um faire Vergleiche zu machen
- Diagramme sind besonders hilfreich, um Ausreißer zu erkennen
- Keyword-Heatmap zeigt sofort, welche Modelle welche Konzepte komplett verpassen
- Prompt-Performance-Grafiken helfen, Strategien gezielt zu verbessern

---
