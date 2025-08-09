#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vergleichsskript für LLM Keyword-Analysen
========================================
- Liest alle analyse_summary.json unter LLM_ROOT
- Sortiert Modelle nach F1-Score
- Erstellt Diagramme:
  * Top-N Modelle (F1)
  * Keyword-Abdeckungs-Heatmap
  * Prompt-Performance pro Modell
  * Gesamt-Prompt-Performance aller Modelle
- Speichert alles unter LLM_ROOT/analyse/global_comparison/
- Nutzt ENV-Variablen aus .env
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------------
# Load ENV
# ---------------------------------
load_dotenv()
LLM_ROOT = Path(os.getenv("LLM_ROOT")).resolve()
LLM_KEYWORDS = Path(os.getenv("LLM_KEYWORDS")).resolve()

if not LLM_ROOT.exists() or not LLM_KEYWORDS.exists():
    raise SystemExit("❌ LLM_ROOT oder LLM_KEYWORDS aus .env nicht gefunden.")

# ---------------------------------
# Output folder
# ---------------------------------
out_dir = LLM_ROOT / "analyse" / "global_comparison"
out_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------
# Collect summaries
# ---------------------------------
summaries = []
for summary_file in LLM_ROOT.rglob("analyse_summary.json"):
    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        data["summary_path"] = str(summary_file)
        data["per_message_path"] = str(Path(summary_file).parent / "analyse_per_message.csv")
        summaries.append(data)

if not summaries:
    raise SystemExit("⚠️ Keine analyse_summary.json gefunden.")

df = pd.DataFrame(summaries)
df_sorted = df.sort_values("f1", ascending=False).reset_index(drop=True)
df_sorted.to_csv(out_dir / "models_sorted.csv", index=False)
print(f"📄 Modelle sortiert gespeichert unter: {out_dir/'models_sorted.csv'}")

# ---------------------------------
# Plot Top-N by F1
# ---------------------------------
top_n = 10
plt.figure(figsize=(10, 6))
sns.barplot(data=df_sorted.head(top_n), x="f1", y="ModelKey", palette="viridis")
plt.xlabel("F1-Score")
plt.ylabel("Model")
plt.title(f"Top-{top_n} Modelle nach F1-Score")
plt.tight_layout()
plt.savefig(out_dir / "topN_f1.png", dpi=150)
plt.close()
print(f"📊 Top-{top_n} F1-Diagramm gespeichert.")

# ---------------------------------
# Keyword heatmap
# ---------------------------------
keywords_df = pd.read_csv(LLM_KEYWORDS)
# flexible Keywordspalten suchen
if "Keyword" in keywords_df.columns:
    ref_keywords = sorted(set(str(v).strip().lower() for v in keywords_df["Keyword"] if str(v).strip()))
else:
    kw_cols = [c for c in keywords_df.columns if c.lower().startswith("w")]
    if kw_cols:
        ref_keywords = sorted(set(str(v).strip().lower() for c in kw_cols for v in keywords_df[c] if str(v).strip()))
    else:
        ref_keywords = []

heatmap_data = pd.DataFrame(0, index=df_sorted["ModelKey"], columns=ref_keywords)
for _, row in df_sorted.iterrows():
    matched = set(map(str.lower, row.get("all_matched_keywords", [])))
    for kw in matched:
        if kw in heatmap_data.columns:
            heatmap_data.loc[row["ModelKey"], kw] = 1

plt.figure(figsize=(max(8, len(ref_keywords)*0.4), len(df_sorted)*0.4))
sns.heatmap(heatmap_data, cmap="Greens", cbar_kws={'label': 'Keyword gefunden (1=ja,0=nein)'})
plt.xlabel("Keyword")
plt.ylabel("Model")
plt.title("Keyword-Abdeckung pro Modell")
plt.tight_layout()
plt.savefig(out_dir / "keyword_heatmap.png", dpi=150)
plt.close()
print("📊 Keyword-Heatmap gespeichert.")

# ---------------------------------
# Prompt performance per model
# ---------------------------------
for _, row in df_sorted.iterrows():
    per_msg_path = Path(row["per_message_path"])
    if not per_msg_path.exists():
        continue
    pm_df = pd.read_csv(per_msg_path)
    avg_per_prompt = pm_df.groupby("MessageIndex")["F1"].mean()

    plt.figure(figsize=(8, 4))
    sns.lineplot(x=avg_per_prompt.index, y=avg_per_prompt.values, marker="o")
    plt.xlabel("Message Index")
    plt.ylabel("Durchschn. F1")
    plt.title(f"Prompt-Performance: {row['ModelKey']}")
    plt.ylim(0, 1)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_dir / f"prompt_performance_{row['ModelKey']}.png", dpi=150)
    plt.close()

print("📊 Prompt-Performance-Diagramme pro Modell gespeichert.")

# ---------------------------------
# Gesamt-Prompt-Performance aller Modelle
# ---------------------------------
plt.figure(figsize=(10, 6))
for _, row in df_sorted.iterrows():
    per_msg_path = Path(row["per_message_path"])
    if not per_msg_path.exists():
        continue
    pm_df = pd.read_csv(per_msg_path)
    avg_per_prompt = pm_df.groupby("MessageIndex")["F1"].mean()
    plt.plot(avg_per_prompt.index, avg_per_prompt.values, marker="o", label=row["ModelKey"])

plt.xlabel("Message Index")
plt.ylabel("Durchschn. F1")
plt.title("Prompt-Performance aller Modelle")
plt.ylim(0, 1)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize="small")
plt.tight_layout()
plt.savefig(out_dir / "prompt_performance.png", dpi=150, bbox_inches="tight")
plt.close()

print("📊 Gesamt-Prompt-Performance-Diagramm gespeichert.")

# ---------------------------------
# Top-5 keywords per model
# ---------------------------------
top_keywords_rows = []
for _, row in df_sorted.iterrows():
    counts = row.get("matched_keyword_counts", [])
    if not counts:
        continue
    top5 = sorted(counts, key=lambda x: (-x["count"], x["keyword"]))[:5]
    for kw in top5:
        top_keywords_rows.append({
            "ModelKey": row["ModelKey"],
            "Keyword": kw["keyword"],
            "Count": kw["count"]
        })

pd.DataFrame(top_keywords_rows).to_csv(out_dir / "keyword_top5.csv", index=False)
print(f"📄 Top-5 Keywords pro Modell gespeichert unter: {out_dir/'keyword_top5.csv'}")

print(f"\n✅ Vergleich abgeschlossen. Ergebnisse in: {out_dir}")
