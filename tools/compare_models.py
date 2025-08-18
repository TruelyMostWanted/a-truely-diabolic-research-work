#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vergleichsskript für LLM Keyword-Analysen (robust & matplotlib-only)

Was es tut:
- Sammelt alle analyse_summary.json unter LLM_ROOT (rekursiv)
- Normiert die Felder (Listen/Dicts aus JSON)
- Exportiert eine sortierte Modell-Liste (nach F1)
- Erzeugt Diagramme unter LLM_ROOT/analyse/global_comparison/:
  * Top-N Modelle (F1)  [--top N]
  * Keyword-Heatmap (NUR Keywords aus keyword_list.csv, Reihenfolge aus CSV)
  * Prompt-Performance pro Modell (Ø-F1 je PromptIndex = Assistant-Antwort)
  * Gesamt-Prompt-Performance (Top-N Modelle; mit --all-lines optional alle)
  * Top-5 Keywords pro Modell (CSV)

Erwartungen (.env):
- LLM_ROOT=../large-language-models
- LLM_KEYWORDS=../input/keyword_list.csv
"""

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, List, Dict, Tuple

# -----------------------------
# CLI & ENV
# -----------------------------
load_dotenv()

parser = argparse.ArgumentParser(description="Vergleicht Modelle anhand der Analyse-Ergebnisse.")
parser.add_argument("--top", type=int, default=10, help="Anzahl Top-Modelle für Rangliste & Gesamt-Prompt-Plot (Default: 10)")
parser.add_argument("--all-lines", action="store_true", help="Zeichne alle Modelle im Gesamt-Prompt-Plot (kann unübersichtlich werden)")
args = parser.parse_args()

def _must_path(env_key: str) -> Path:
    val = os.getenv(env_key)
    if not val:
        raise SystemExit(f"❌ {env_key} nicht gesetzt. Bitte in .env definieren.")
    p = Path(val).resolve()
    if not p.exists():
        raise SystemExit(f"❌ Pfad aus {env_key} nicht gefunden: {p}")
    return p

LLM_ROOT = _must_path("LLM_ROOT")
LLM_KEYWORDS = _must_path("LLM_KEYWORDS")

# -----------------------------
# Ausgabeordner
# -----------------------------
out_dir = LLM_ROOT / "analyse" / "global_comparison"
out_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def _as_list(obj: Any) -> List:
    if isinstance(obj, list):
        return obj
    if obj is None:
        return []
    if isinstance(obj, str):
        s = obj.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                return json.loads(s)
            except Exception:
                return []
        if "," in s:
            return [x.strip() for x in s.split(",") if x.strip()]
        return [s] if s else []
    return [obj]

def _as_list_of_dicts(obj: Any) -> List[Dict]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, str):
        s = obj.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                val = json.loads(s)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
            except Exception:
                return []
    return []

def _read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

# --- Keywords aus keyword_list.csv laden (nur diese, Reihenfolge beibehalten) ---
def _load_keywords_reference_strict_order(csv_path: Path) -> List[str]:
    """
    Nimmt NUR die Keywords aus keyword_list.csv. Reihenfolge = CSV-Reihenfolge.
    Akzeptiert:
      - Spalte 'Keyword'
      - oder Spalten w1, w2, ... (falls vorhanden -> in Reihenfolge dieser Spalten)
      - sonst: ERZWUNGENER ABBRUCH, um „Fremdwerte“ zu vermeiden.
    Filter:
      - trims
      - entfernt Duplikate unter Beibehaltung der Reihenfolge
      - ignoriert reine Zahlen / Tokens ohne Buchstaben
    """
    import re
    df = pd.read_csv(csv_path)
    cols = [c.strip() for c in df.columns]

    def has_letter(s: str) -> bool:
        return bool(re.search(r"[A-Za-zÄÖÜäöü]", s))

    ordered = []

    if "Keyword" in cols:
        ordered = [str(v).strip() for v in df["Keyword"].tolist() if str(v).strip()]
    else:
        wcols = [c for c in cols if re.fullmatch(r"[Ww]\d+", c)]
        if wcols:
            for c in wcols:
                ordered.extend([str(v).strip() for v in df[c].tolist() if str(v).strip()])
        else:
            raise SystemExit("❌ keyword_list.csv hat weder eine Spalte 'Keyword' noch 'w1..wN' – bitte anpassen.")

    # Duplikate entfernen, Reihenfolge erhalten, nur mit Buchstaben
    seen = set()
    clean = []
    for tok in ordered:
        tok_lower = tok.lower()
        if tok_lower in seen:
            continue
        if not has_letter(tok_lower):
            continue  # vermeide reine Zahlen
        clean.append(tok_lower)
        seen.add(tok_lower)

    if not clean:
        raise SystemExit("❌ keyword_list.csv lieferte keine gültigen Keywords nach Filterung.")
    return clean

# -----------------------------
# Summaries einsammeln
# -----------------------------
summaries: List[Dict] = []
for summary_file in LLM_ROOT.rglob("analyse_summary.json"):
    try:
        data = _read_json(summary_file)
    except Exception:
        print(f"⚠️ Kann JSON nicht lesen: {summary_file}")
        continue
    data["summary_path"] = str(summary_file)
    data["per_message_path"] = str(Path(summary_file).parent / "analyse_per_message.csv")
    data["all_matched_keywords"] = _as_list(data.get("all_matched_keywords"))
    data["matched_keyword_counts"] = _as_list_of_dicts(data.get("matched_keyword_counts"))
    data["f1"] = _safe_float(data.get("f1"))
    summaries.append(data)

if not summaries:
    raise SystemExit("⚠️ Keine analyse_summary.json gefunden.")

df = pd.DataFrame(summaries)
df_sorted = df.sort_values("f1", ascending=False).reset_index(drop=True)
(df_sorted).to_csv(out_dir / "models_sorted.csv", index=False, encoding="utf-8")
print(f"📄 Modelle sortiert gespeichert unter: {out_dir/'models_sorted.csv'}")

# -----------------------------
# Top-N Barplot (F1)
# -----------------------------
top_n = max(1, int(args.top))
top_df = df_sorted.head(top_n).copy()

plt.figure(figsize=(10, max(4, 0.5 * len(top_df))))
y = list(reversed(top_df["ModelKey"].tolist()))
x = list(reversed(top_df["f1"].tolist()))
plt.barh(y, x)
plt.xlabel("F1-Score")
plt.ylabel("Model")
plt.title(f"Top-{top_n} Modelle nach F1-Score")
plt.tight_layout()
plt.savefig(out_dir / "topN_f1.png", dpi=150)
plt.close()
print(f"📊 Top-{top_n} F1-Diagramm gespeichert.")

# -----------------------------
# Keyword-Heatmap (NUR Keywords aus keyword_list.csv)
# -----------------------------
try:
    ref_keywords_ordered = _load_keywords_reference_strict_order(LLM_KEYWORDS)
except SystemExit as e:
    print(str(e))
    ref_keywords_ordered = []

if ref_keywords_ordered:
    # Spalten = Modelle (ModelKey), Zeilen = Keywords (in CSV-Reihenfolge)
    model_keys = df_sorted["ModelKey"].tolist()
    # Matrix: len(keywords) x len(models)
    H = np.zeros((len(ref_keywords_ordered), len(model_keys)), dtype=int)

    # Erzeuge eine Map ModelKey -> set(matched_keywords_lower)
    mk_to_matches = []
    for _, row in df_sorted.iterrows():
        matched = {str(k).lower() for k in _as_list(row.get("all_matched_keywords"))}
        mk_to_matches.append(matched)

    for j, matched_set in enumerate(mk_to_matches):
        for i, kw in enumerate(ref_keywords_ordered):
            if kw in matched_set:
                H[i, j] = 1

    # Plotten: y=Keywords (CSV-Reihenfolge), x=Modelle
    fig_w = max(10, min(50, 0.25 * len(model_keys)))
    fig_h = max(10, min(50, 0.25 * len(ref_keywords_ordered)))
    plt.figure(figsize=(fig_w, fig_h))
    plt.imshow(H, aspect="auto", interpolation="nearest")
    cbar = plt.colorbar()
    cbar.set_label("Keyword gefunden (1=ja, 0=nein)")

    # x-Ticks (Modelle)
    if len(model_keys) <= 60:
        plt.xticks(ticks=range(len(model_keys)), labels=model_keys, rotation=90, fontsize=8)
    else:
        step = max(1, len(model_keys)//60)
        ticks = list(range(0, len(model_keys), step))
        labels = [model_keys[k] for k in ticks]
        plt.xticks(ticks=ticks, labels=labels, rotation=90, fontsize=8)

    # y-Ticks (Keywords)
    if len(ref_keywords_ordered) <= 60:
        plt.yticks(ticks=range(len(ref_keywords_ordered)), labels=ref_keywords_ordered, fontsize=8)
    else:
        step = max(1, len(ref_keywords_ordered)//60)
        ticks = list(range(0, len(ref_keywords_ordered), step))
        labels = [ref_keywords_ordered[k] for k in ticks]
        plt.yticks(ticks=ticks, labels=labels, fontsize=8)

    plt.xlabel("Modelle")
    plt.ylabel("Keywords (aus keyword_list.csv)")
    plt.title("Keyword-Abdeckung (nur Keywords aus keyword_list.csv)")
    plt.tight_layout()
    plt.savefig(out_dir / "keyword_heatmap.png", dpi=150)
    plt.close()
    print("📊 Keyword-Heatmap gespeichert.")
else:
    print("ℹ️ Heatmap übersprungen (keyword_list.csv ungeeignet oder leer nach Filterung).")

# -----------------------------
# Prompt-Performance pro Modell
# -----------------------------
def _avg_per_prompt(per_msg_csv: Path) -> Tuple[List[int], List[float]]:
    if not per_msg_csv.exists():
        return [], []
    try:
        dfp = pd.read_csv(per_msg_csv)
    except Exception:
        return [], []
    if "MessageIndex" not in dfp.columns or "F1" not in dfp.columns:
        return [], []

    # Nur Assistant-Nachrichten: in unserer Sequenz sind das die GERADEN Indizes
    df_assist = dfp[dfp["MessageIndex"] % 2 == 0].copy()
    if df_assist.empty:
        return [], []

    # Mappe MessageIndex 2,4,6,... -> PromptIndex 1,2,3,...
    df_assist["PromptIndex"] = (df_assist["MessageIndex"] // 2).astype(int)

    g = df_assist.groupby("PromptIndex", as_index=True)["F1"].mean().sort_index()
    return g.index.tolist(), g.values.tolist()

for _, row in df_sorted.iterrows():
    per_msg_path = Path(row["per_message_path"])
    xi, yi = _avg_per_prompt(per_msg_path)
    if not xi:
        continue
    plt.figure(figsize=(8, 4))
    plt.plot(xi, yi, marker="o")
    plt.xlabel("Prompt Index (Assistant)")
    plt.ylabel("Durchschn. F1")
    plt.title(f"Prompt-Performance: {row['ModelKey']}")
    plt.ylim(0, 1)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    safe_name = str(row["ModelKey"]).replace("/", "_")
    plt.savefig(out_dir / f"prompt_performance_{safe_name}.png", dpi=150)
    plt.close()

print("📊 Prompt-Performance-Diagramme pro Modell gespeichert.")

# -----------------------------
# Gesamt-Prompt-Performance (Top-N oder alle)
# -----------------------------
plt.figure(figsize=(10, 6))
legend_labels = []

rows_iter = df_sorted.iterrows() if args.all_lines else df_sorted.head(top_n).iterrows()
for _, row in rows_iter:
    per_msg_path = Path(row["per_message_path"])
    xi, yi = _avg_per_prompt(per_msg_path)
    if not xi:
        continue
    plt.plot(xi, yi, marker="o")
    legend_labels.append(row["ModelKey"])

plt.xlabel("Prompt Index (Assistant)")
plt.ylabel("Durchschn. F1")
plt.title("Prompt-Performance (Top-{} Modelle)".format(top_n) if not args.all_lines else "Prompt-Performance (alle Modelle)")
plt.ylim(0, 1)
plt.grid(True, linestyle="--", alpha=0.5)
if legend_labels:
    plt.legend(legend_labels, bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
plt.tight_layout()
plt.savefig(out_dir / "prompt_performance.png", dpi=150, bbox_inches="tight")
plt.close()

print("📊 Gesamt-Prompt-Performance-Diagramm gespeichert.")

# -----------------------------
# Top-5 Keywords pro Modell (CSV)
# -----------------------------
rows_top5 = []
for _, row in df_sorted.iterrows():
    counts = _as_list_of_dicts(row.get("matched_keyword_counts"))
    if not counts:
        continue
    top5 = sorted(counts, key=lambda x: (-int(x.get("count", 0)), str(x.get("keyword", ""))))[:5]
    for kw in top5:
        rows_top5.append({
            "ModelKey": row["ModelKey"],
            "Keyword": kw.get("keyword", ""),
            "Count": int(kw.get("count", 0)),
        })

pd.DataFrame(rows_top5).to_csv(out_dir / "keyword_top5.csv", index=False, encoding="utf-8")
print(f"📄 Top-5 Keywords pro Modell gespeichert unter: {out_dir/'keyword_top5.csv'}")

print(f"\n✅ Vergleich abgeschlossen. Ergebnisse in: {out_dir}")
