# Strategie 0: Offene Suche mit offenen Fragen nach Antworten, keine Limitierungen

---

## ROLLE FESTLEGEN

#### Prompt 0: Rolle erzwingen
Agiere im Nachfolgenden als Experte im Bereich von der Erstellung von Optimierungsproblemen. Du wirst offene Fragen und Anweisungen erhalten.

---

## WARM-UP PROMPTING 

#### Prompt 1: Wissen über Optimierungsprobleme
Liste Informationen über die verschiedenen Kategorien, Arten und Typen von Optimierungsproblemen.

#### Prompt 2: Wissen über Softwareentwicklung mit SCRUM
Was weißt du über Software Entwicklung mit SCRUM als agiler Methode? Liste mir alle Komponenten und Schritte dieser Methodik auf.

#### Prompt 3: Wissen über Anforderungs-Management 
Im Kontext von SCRUM: Analysiere wie man mittels Natürlicher Sprache Anforderungen für den Prozess der Software-Entwicklung extrahiert, designt und evaluiert werden können

#### Prompt 4: Wissen über Stressentwicklung
Welche Prozesse, Elemente und Faktoren existieren beim Entwickeln mit Scrum, die Personen zur kognitiven Belastung und Stressentwicklung bringen.

#### Prompt 5: Typische Ziele und Nebenbedingungen in SCRUM
In SCRUM: Was sind die typischen Ziele und Nebenbedingungen für ein Unternehmen, anhand dessen Entscheidungen getroffen werden können

---

## MODELLIERUNG

#### Prompt 6: Entities und Relationen für ein Domänenmodell
Lass uns nun ein Domänenmodel für ein Unternehmen das mit SCRUM arbeitet erstellen.
Ich brauche 2 Tabellen: "Entities" mit Name,Beschreibung und 1-8 Attributen sowie eine Tabelle "Relationen" mit Name,Beschreibung,Entität1,Entität2 und auch den Kardinalitäten

#### Prompt 7: Nenne Ziele und Nebenbedingungen
Erstelle nun eine Liste von Zielen und Nebenbedingungen für dieses Modell. Weise diesen jeweils 1 von 3 Kriterien zu: Must-Match, May-Match und Cannot-Match

#### Prompt 8: Entscheidungsvariablen definieren
Erstelle nun Entscheidungsvariablen (boolean und numerisch)

#### Prompt 9: Mathematische Repräsentation
Nutze ALLE BISHERIGEN DATEN und formuliere das Optimierungsproblen mathematisch bzw. logisch. 
Erstelle eine LaTeX Datei und speichere dort: Mengen, Indices, Entscheidungsvariablen, Ziele und Nebenbedingunen.

#### Prompt 10: Visualisierung durch Mermaid.js
Verwandele das erstelle Domänen-Optimierungs-Modell nun in eine strukturelle Graphen-Repräsentation.
Verwende dafür die Mermaid Live Editor Syntax.
Der Graph MUSS die Entitäten, Attribute, Relationen, Ziele und Bedingungen enthalten
