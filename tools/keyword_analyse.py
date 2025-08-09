#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Keyword Analysis for LLM Chats with Strategy Prompt Normalization + Aggregation + .env
=====================================================================================

- Pfadschema: <root>/<local-llm|remote-llms>/<model>/<size>/<strategy>/<version>/chat.json
  * size darf Dezimalstellen haben: 7.2b, 3.5b, 24b ...
- Strategy-Prompts aus: input/strategyX_prompts.csv  (toleriert: strategyX_promts.csv)
- Normalisiert Chats auf die erwartete Prompt-Anzahl
- Flexible Keyword-CSV (Keyword | w1..wN | generische Textspalten)
- Per-Chat + globale Aggregation + XML (ModelKey)
- ENV-Unterstützung via .env + GitHub Actions (CLI-Args optional)
- NEU: speichert pro Nachricht `Matched_Keywords` + aggregiert alle Treffer im Summary
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Set
import pandas as pd
import re
import spacy
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from collections import Counter

SIZE_RE = re.compile(r"^\d+(?:\.\d+)?[bB]$")   # 8b, 24b, 7.2b, 3.5b
W_COL_RE  = re.compile(r"^w\d+$", re.IGNORECASE)


# ----------------------------
# Discovery & path parsing
# ----------------------------
def find_chat_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for sub in ("local-llm", "remote-llms"):
        base = root / sub
        if base.exists():
            files.extend(base.rglob("chat.json"))
    return sorted(files)


def parse_triplet_from_path(chat_path: Path) -> Tuple[str, str, str]:
    parts = chat_path.parts
    model = strategy = version = "unknown"

    # find scope anchor
    anchor = None
    for i, p in enumerate(parts):
        if p in ("local-llm", "remote-llms"):
            anchor = i
            break
    if anchor is None:
        return model, strategy, version

    if anchor + 1 >= len(parts):
        return model, strategy, version
    m = parts[anchor + 1]

    # size
    if anchor + 2 < len(parts) and SIZE_RE.fullmatch(parts[anchor + 2]):
        size = parts[anchor + 2]
        model = f"{m}-{size}"
        if anchor + 3 < len(parts):
            strategy = parts[anchor + 3]
        if anchor + 4 < len(parts):
            version = parts[anchor + 4]
    else:
        # kein expliziter size-Ordner
        model = m
        if anchor + 2 < len(parts):
            strategy = parts[anchor + 2]
        if anchor + 3 < len(parts):
            version = parts[anchor + 3]

    # sanity: strategy sollte s<digits> sein; notfalls weich fallbacken
    if not re.fullmatch(r"s\d+", str(strategy).lower()):
        if re.fullmatch(r"v\d+", str(strategy).lower()):
            strategy = "s1"  # fallback
    return model, strategy, version


# ----------------------------
# Strategy prompts
# ----------------------------
def load_strategy_prompts(input_root: Path, strategy: str) -> List[str]:
    m = re.match(r"s(\d+)", str(strategy).lower())
    if not m:
        raise SystemExit(f"❌ Strategie '{strategy}' nicht erkennbar. Erwartet Format sX.")
    num = m.group(1)

    preferred = input_root / f"strategy{num}_prompts.csv"
    tolerated = input_root / f"strategy{num}_promts.csv"  # Tippfehler-tolerant

    if preferred.exists():
        csv_path = preferred
    elif tolerated.exists():
        csv_path = tolerated
        print(f"⚠️  Using tolerated filename: {tolerated.name}")
    else:
        raise SystemExit(f"❌ Prompt-CSV nicht gefunden: {preferred} (oder {tolerated.name})")

    df = pd.read_csv(csv_path)
    if "Prompt" in df.columns:
        prompts = [str(v).strip() for v in df["Prompt"] if str(v).strip()]
    else:
        text_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
        if not text_cols:
            raise SystemExit(f"❌ Keine Textspalten in {csv_path} gefunden.")
        prompts = [str(v).strip() for v in df[text_cols[0]] if str(v).strip()]
    return prompts


# ----------------------------
# Chat loading & normalization
# ----------------------------
def load_and_normalize_chat(chat_path: Path, expected_prompts: List[str]) -> List[str]:
    """
    Returns messages interleaved [user1, assistant1, ...], normalized
    to len(expected_prompts) user turns (missing -> '<empty>').
    """
    with chat_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    user_msgs, assistant_msgs = [], []
    for entry in data:
        chat = entry.get("chat", {})
        msgs = chat.get("history", {}).get("messages", {})
        for msg in msgs.values():
            role = msg.get("role")
            txt = (msg.get("content") or "").strip()
            if role == "user":
                user_msgs.append(txt)
            elif role == "assistant":
                assistant_msgs.append(txt)

    n_expected = len(expected_prompts)
    # pad/crop user
    if len(user_msgs) < n_expected:
        user_msgs.extend(["<empty>"] * (n_expected - len(user_msgs)))
    else:
        user_msgs = user_msgs[:n_expected]
    # pad/crop assistant
    if len(assistant_msgs) < n_expected:
        assistant_msgs.extend(["<empty>"] * (n_expected - len(assistant_msgs)))
    else:
        assistant_msgs = assistant_msgs[:n_expected]

    combined = []
    for u, a in zip(user_msgs, assistant_msgs):
        combined.append(u)
        combined.append(a)
    return combined


# ----------------------------
# Keyword reference
# ----------------------------
def _is_text_col(s: pd.Series) -> bool:
    return s.dtype == "object" or pd.api.types.is_string_dtype(s)

def _normalize_kw(x: str) -> str:
    return x.strip().lower()

def load_keyword_reference(csv_path: Path) -> Set[str]:
    df = pd.read_csv(csv_path)
    cols = list(df.columns)

    if "Keyword" in cols:
        return {_normalize_kw(v) for v in df["Keyword"] if isinstance(v, str) and v.strip()}

    w_cols = [c for c in cols if W_COL_RE.match(c)]
    if w_cols:
        kws = []
        for c in w_cols:
            kws.extend([_normalize_kw(v) for v in df[c] if isinstance(v, str) and v.strip()])
        return set(kws)

    meta = {"SourceID", "SourceTitle", "wCount"}
    text_cols = [c for c in cols if c not in meta and _is_text_col(df[c])]
    if not text_cols:
        raise SystemExit("❌ No suitable keyword columns found in CSV. Provide 'Keyword' or w1..wN or text columns.")
    kws = []
    for c in text_cols:
        kws.extend([_normalize_kw(v) for v in df[c] if isinstance(v, str) and v.strip()])
    return set(kws)


# ----------------------------
# NLP & scoring
# ----------------------------
def extract_keywords(doc) -> Set[str]:
    # noun chunks (lemmatized) + named entities (surface)
    chunks = [
        " ".join(t.lemma_.lower() for t in nc if not t.is_punct and not t.is_space)
        for nc in doc.noun_chunks
    ]
    chunks = [c for c in chunks if c and any(ch.isalnum() for ch in c)]
    ents = [e.text.lower() for e in doc.ents if e.text.strip()]
    return set(chunks + ents)

def compute_scores(predicted: Set[str], reference: Set[str]):
    tp = len(predicted & reference)
    fp = len(predicted - reference)
    fn = len(reference - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1, tp, fp, fn


# ----------------------------
# Per-chat analysis
# ----------------------------
def analyze_single_chat(chat_path: Path, nlp, reference_keywords: Set[str],
                        strategy_prompts: List[str], batch_size: int = 64) -> Dict:
    model, strategy, version = parse_triplet_from_path(chat_path)
    model_key = f"{model}-{strategy}-{version}"
    messages = load_and_normalize_chat(chat_path, strategy_prompts)

    rows = []
    agg_tp = agg_fp = agg_fn = 0
    matched_counter = Counter()  # NEU: globale Trefferhäufigkeit im Chat

    for i, doc in enumerate(nlp.pipe(messages, batch_size=batch_size)):
        predicted = extract_keywords(doc)
        matched = predicted & reference_keywords                     # NEU
        precision, recall, f1, tp, fp, fn = compute_scores(predicted, reference_keywords)
        agg_tp += tp; agg_fp += fp; agg_fn += fn
        if matched:
            matched_counter.update(matched)

        rows.append({
            "ModelKey": model_key,
            "MessageIndex": i + 1,
            "Predicted_Keywords": ", ".join(sorted(predicted)),
            "Matched_Keywords": ", ".join(sorted(matched)),          # NEU
            "Precision": precision, "Recall": recall, "F1": f1,
            "TP": tp, "FP": fp, "FN": fn,
            "Text": doc.text,
        })

    # write per-chat artifacts
    per_message_csv = chat_path.parent / "analyse_per_message.csv"
    pd.DataFrame(rows).to_csv(per_message_csv, index=False)

    prec = agg_tp / (agg_tp + agg_fp) if (agg_tp + agg_fp) else 0.0
    rec  = agg_tp / (agg_tp + agg_fn) if (agg_tp + agg_fn) else 0.0
    f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0

    # NEU: aggregierte Trefferlisten
    matched_keyword_counts = sorted(
        [{"keyword": k, "count": int(v)} for k, v in matched_counter.items()],
        key=lambda x: (-x["count"], x["keyword"])
    )
    all_matched_keywords = sorted(matched_counter.keys())
    matched_unique_count = len(all_matched_keywords)

    summary = {
        "ModelKey": model_key,
        "model": model, "strategy": strategy, "version": version,
        "messages": len(messages),
        "expected_prompts": strategy_prompts,
        "TP": agg_tp, "FP": agg_fp, "FN": agg_fn,
        "precision": prec, "recall": rec, "f1": f1,
        "matched_unique_count": matched_unique_count,                # NEU
        "all_matched_keywords": all_matched_keywords,                # NEU
        "matched_keyword_counts": matched_keyword_counts,            # NEU
        "per_message_csv": str(per_message_csv),
        "chat_path": str(chat_path),
    }
    with (chat_path.parent / "analyse_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


# ----------------------------
# Global aggregation
# ----------------------------
def ensure_analyse_root(root: Path) -> Path:
    out = root / "analyse"
    out.mkdir(parents=True, exist_ok=True)
    return out


def aggregate_and_write(all_chat_summaries: List[Dict], analyse_root: Path, strategy_prompts_map: Dict[str, List[str]]):
    df = pd.DataFrame(all_chat_summaries).sort_values(["model", "strategy", "version"]).reset_index(drop=True)

    # all chats
    all_csv = analyse_root / "all_chats_summary.csv"
    df.to_csv(all_csv, index=False)

    # per strategy (group by model+strategy)
    strat_rows = []
    for (m, s), g in df.groupby(["model", "strategy"], dropna=False):
        tp, fp, fn = g["TP"].sum(), g["FP"].sum(), g["FN"].sum()
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec  = tp / (tp + fn) if (tp + fn) else 0.0
        f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        strat_rows.append({
            "StrategyKey": f"{m}-{s}",
            "Model": m, "Strategy": s,
            "Chats": int(g.shape[0]),
            "TP": int(tp), "FP": int(fp), "FN": int(fn),
            "Precision": prec, "Recall": rec, "F1": f1,
        })
    pd.DataFrame(strat_rows).to_csv(analyse_root / "per_strategy_summary.csv", index=False)

    # per model
    model_rows = []
    for m, g in df.groupby("model", dropna=False):
        tp, fp, fn = g["TP"].sum(), g["FP"].sum(), g["FN"].sum()
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec  = tp / (tp + fn) if (tp + fn) else 0.0
        f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        model_rows.append({
            "Model": m,
            "Chats": int(g.shape[0]),
            "TP": int(tp), "FP": int(fp), "FN": int(fn),
            "Precision": prec, "Recall": rec, "F1": f1,
        })
    pd.DataFrame(model_rows).to_csv(analyse_root / "per_model_summary.csv", index=False)

    # overall
    tp, fp, fn = df["TP"].sum(), df["FP"].sum(), df["FN"].sum()
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    overall = {
        "chats": int(df.shape[0]),
        "TP": int(tp), "FP": int(fp), "FN": int(fn),
        "precision": prec, "recall": rec, "f1": f1,
        "all_chats_summary_csv": str(all_csv),
    }
    with (analyse_root / "overall_summary.json").open("w", encoding="utf-8") as f:
        json.dump(overall, f, indent=2, ensure_ascii=False)

    # store strategy prompts centrally
    with (analyse_root / "strategy_prompts.json").open("w", encoding="utf-8") as f:
        json.dump(strategy_prompts_map, f, indent=2, ensure_ascii=False)

    # XML export with ModelKey + aggregations
    xml_root = ET.Element("LLMKeywordComparison")
    ET.SubElement(xml_root, "Meta", attrib={"totalChats": str(df.shape[0])})

    for _, row in df.iterrows():
        ET.SubElement(xml_root, "ChatSummary", attrib={
            "ModelKey": row["ModelKey"],
            "messages": str(row["messages"]),
            "TP": str(int(row["TP"])),
            "FP": str(int(row["FP"])),
            "FN": str(int(row["FN"])),
            "precision": f'{row["precision"]:.6f}',
            "recall": f'{row["recall"]:.6f}',
            "f1": f'{row["f1"]:.6f}',
        })

    aggr = ET.SubElement(xml_root, "Aggregations")
    per_model_node = ET.SubElement(aggr, "PerModel")
    for r in model_rows:
        ET.SubElement(per_model_node, "ModelSummary", attrib={
            "Model": r["Model"],
            "Chats": str(r["Chats"]),
            "TP": str(int(r["TP"])),
            "FP": str(int(r["FP"])),
            "FN": str(int(r["FN"])),
            "precision": f'{r["Precision"]:.6f}',
            "recall": f'{r["Recall"]:.6f}',
            "f1": f'{r["F1"]:.6f}',
        })
    per_strategy_node = ET.SubElement(aggr, "PerStrategy")
    for r in strat_rows:
        ET.SubElement(per_strategy_node, "StrategySummary", attrib={
            "StrategyKey": r["StrategyKey"],
            "Chats": str(r["Chats"]),
            "TP": str(int(r["TP"])),
            "FP": str(int(r["FP"])),
            "FN": str(int(r["FN"])),
            "precision": f'{r["Precision"]:.6f}',
            "recall": f'{r["Recall"]:.6f}',
            "f1": f'{r["F1"]:.6f}',
        })

    ET.ElementTree(xml_root).write(analyse_root / "comparison.xml", encoding="utf-8", xml_declaration=True)


# ----------------------------
# Main
# ----------------------------
def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getenv("LLM_ROOT"))
    ap.add_argument("--keywords", default=os.getenv("LLM_KEYWORDS"))
    ap.add_argument("--input_root", default=os.getenv("LLM_INPUT_ROOT"))
    ap.add_argument("--spacy_model", default=os.getenv("LLM_SPACY_MODEL", "en_core_web_sm"))
    ap.add_argument("--batch", type=int, default=int(os.getenv("LLM_BATCH", "64")))
    args = ap.parse_args()

    if not args.root or not args.keywords or not args.input_root:
        raise SystemExit("❌ Missing parameters. Set .env (LLM_ROOT, LLM_KEYWORDS, LLM_INPUT_ROOT) or pass CLI args.")

    root = Path(args.root).resolve()
    kw_path = Path(args.keywords).resolve()
    input_root = Path(args.input_root).resolve()

    reference_keywords = load_keyword_reference(kw_path)

    try:
        nlp = spacy.load(args.spacy_model, disable=[])
    except OSError as e:
        raise SystemExit(
            f"❌ Could not load spaCy model '{args.spacy_model}'. "
            f"Install with: python -m spacy download {args.spacy_model}"
        ) from e
    if not nlp.has_pipe("parser"):
        nlp.enable_pipe("parser")
    if not (nlp.has_pipe("senter") or nlp.has_pipe("sentencizer")):
        nlp.add_pipe("sentencizer", first=True)

    chat_files = find_chat_files(root)
    if not chat_files:
        print(f"⚠️  No chat.json files found under: {root}")
        return

    print(f"🔎 Found {len(chat_files)} chat.json files. Starting analysis…")

    summaries = []
    strategy_prompts_map: Dict[str, List[str]] = {}

    for p in chat_files:
        model, strategy, version = parse_triplet_from_path(p)
        print(f"\nModel: {model} | Strategie: {strategy} | Version: {version}")
        print("  chat.json found")
        # load prompts
        try:
            prompts = load_strategy_prompts(input_root, strategy)
        except SystemExit as e:
            print(f"  ⚠️  {e}. Using fallback prompts: [] and continuing.")
            prompts = []
        strategy_prompts_map[strategy] = prompts
        print("  Normalizing to strategy prompts...")
        summaries.append(analyze_single_chat(p, nlp, reference_keywords, prompts, batch_size=args.batch))
        print("  Finished ✅")

    analyse_root = ensure_analyse_root(root)
    aggregate_and_write(summaries, analyse_root, strategy_prompts_map)

    print("\n✅ Done.")
    print("   Per-chat outputs are next to each chat.json (analyse_per_message.csv, analyse_summary.json).")
    print("   Global outputs in:", analyse_root)


if __name__ == "__main__":
    main()
