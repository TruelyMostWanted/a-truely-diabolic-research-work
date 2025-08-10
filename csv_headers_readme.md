# SCRUM Optimierungsdaten – CSV-Struktur

Dieses Dokument beschreibt das Datenformat für die Eingabedateien eines Optimierungsmodells in einem SCRUM-basierten Softwareunternehmen.  
Es werden fünf verschiedene CSV-Dateien verwendet: **Entitäten**, **Relationen**, **Ziele (Goals)**, **Nebenbedingungen (Conditions)** und **Entscheidungsvariablen (Decision Variables)**.

---

## 1. Entities (Entitäten)

**Dateiname:** `entities.csv`

| Spalte        | Typ     | Beschreibung |
|---------------|---------|--------------|
| `ID`          | String  | Eindeutige Bezeichnung der Entität (innerhalb dieser Datei) |
| `Name`        | String  | Lesbarer Name der Entität |
| `Description` | String  | Beschreibung oder Zusatzinformationen |
| `Attribute0`–`Attribute8` | String/Numeric | Bis zu 9 zusätzliche Eigenschaften der Entität, deren Bedeutung projektspezifisch definiert wird |

**Hinweis:**  
- `Name` wird für Referenzen in anderen Dateien verwendet (nicht `ID`).  
- Die Attribute sind generisch benannt, um eine einfache CSV-Struktur zu behalten.  

---

## 2. Relations (Relationen)

**Dateiname:** `relations.csv`

| Spalte           | Typ     | Beschreibung |
|------------------|---------|--------------|
| `ID`             | String  | Eindeutige Bezeichnung der Relation |
| `Name`           | String  | Lesbarer Name der Relation |
| `Description`    | String  | Beschreibung oder Zusatzinformationen |
| `FromEntity`     | String  | Name der Quell-Entität (muss in `entities.csv` vorkommen) |
| `ToEntity`       | String  | Name der Ziel-Entität (muss in `entities.csv` vorkommen) |
| `FromCardinality`| String  | Kardinalität der Beziehung von der Quellseite (z. B. `1`, `n`) |
| `ToCardinality`  | String  | Kardinalität der Beziehung von der Zielseite |
| `Weight`         | Numeric | Optionales Gewicht oder Stärke der Relation |

---

## 3. Goals (Ziele)

**Dateiname:** `goals.csv`

| Spalte           | Typ     | Beschreibung |
|------------------|---------|--------------|
| `ID`             | String  | Eindeutige Bezeichnung des Ziels |
| `Name`           | String  | Lesbarer Name des Ziels |
| `Description`    | String  | Beschreibung oder Zusatzinformationen |
| `IsSum`          | Boolean | `true` = Aggregation über mehrere Werte, `false` = Einzelwert |
| `GoalType`       | String  | Art des Ziels: `Max` oder `Min` |
| `EntityName`     | String  | Name der Entität, auf die sich das Ziel bezieht |
| `EntityAttribute`| String  | Attribut der Entität, das optimiert wird |
| `CriteriaType`   | String  | Typ des Vergleichs oder der Berechnung (projektspezifisch definiert) |
| `Weight`         | Numeric | Gewichtung des Ziels bei Mehrziel-Optimierung |

---

## 4. Conditions (Nebenbedingungen / Constraints)

**Dateiname:** `conditions.csv`

| Spalte           | Typ     | Beschreibung |
|------------------|---------|--------------|
| `ID`             | String  | Eindeutige Bezeichnung der Nebenbedingung |
| `Name`           | String  | Lesbarer Name der Nebenbedingung |
| `Description`    | String  | Beschreibung oder Zusatzinformationen |
| `IsSum`          | Boolean | `true` = Aggregation über mehrere Werte, `false` = Einzelwert |
| `GoalType`       | String  | `Max`, `Min` oder andere Vergleichsarten (abhängig vom Modell) |
| `EntityName`     | String  | Name der Entität, auf die sich die Bedingung bezieht |
| `EntityAttribute`| String  | Attribut der Entität, das geprüft wird |
| `CriteriaType`   | String  | Typ des Vergleichs oder der Prüfung (z. B. `<`, `<=`, `=`, `>=`, `>`) |
| `Weight`         | Numeric | Gewichtung: leer oder ∞ für HardConstraint, positiver Wert für SoftConstraint |

**Hinweis:**  
- **HardConstraint**: `Weight` leer lassen oder sehr hoher Wert (∞).  
- **SoftConstraint**: `Weight` > 0, dieser Wert wird als Strafkosten in die Zielfunktion einbezogen.

---

## 5. Decision Variables (Entscheidungsvariablen)

**Dateiname:** `decision_variables.csv`

| Spalte        | Typ     | Beschreibung |
|---------------|---------|--------------|
| `ID`          | String  | Eindeutige Bezeichnung der Variablen |
| `Name`        | String  | Lesbarer Name der Variablen |
| `Description` | String  | Beschreibung oder Zusatzinformationen |
| `DataType`    | String  | `Binary`, `Integer` oder `Real` |
| `Domain`      | String  | Wertebereich (z. B. `{0,1}` oder `{A,B,C}`) |
| `MinValue`    | Numeric | Untergrenze (falls anwendbar) |
| `MaxValue`    | Numeric | Obergrenze (falls anwendbar) |

---

## Allgemeine Hinweise

- **Referenzen** zwischen Dateien erfolgen über den `Name` einer Entität oder Relation, nicht über `ID`.  
- CSV-Dateien sollten UTF-8-kodiert sein.  
- Numerische Felder sollten Punkt `.` als Dezimaltrennzeichen nutzen.  
- Leere Werte in optionalen Feldern dürfen frei gelassen werden.  
- Kommentare sind in CSV-Dateien nicht erlaubt. Für Notizen bitte separate Dokumentation führen.

---
