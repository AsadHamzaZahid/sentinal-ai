"""One-time export of genuine ModernBERT predictions for the deployed demo.

    python scripts/export_ragtruth_samples.py --test-file data/ragtruth_test.csv

Needs the real model (pip install -r requirements-live.txt) in the usual model folder.
The test file (.csv/.json/.jsonl) must have columns: task_type, source_info, response, label (0/1).
Optional: dataset_name. Edit load_examples() if your column names differ.

All test examples are scored (needed to find real false positives/negatives); metrics use the full test set."""
import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["RAGTRUTH_MODE"] = "live"  # force the real model
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import main  # noqa: E402

PLAN = {"TP": 3, "TN": 3, "FP": 2, "FN": 2}  # 10 samples


def load_examples(path: Path):
    import pandas as pd
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_json(path, lines=path.suffix == ".jsonl")
    missing = {"task_type", "source_info",
               "response", "label"} - set(df.columns)
    if missing:
        sys.exit(f"Test file is missing columns: {missing}")
    if "dataset_name" not in df:
        df["dataset_name"] = ""
    return df.to_dict("records")


def pick(cands, k, rng):
    """Seeded random, preferring a spread across task types."""
    rng.shuffle(cands)
    chosen, seen = [], set()
    for c in cands:
        if len(chosen) < k and c["task_type"] not in seen:
            chosen.append(c)
            seen.add(c["task_type"])
    for c in cands:
        if len(chosen) < k and c not in chosen:
            chosen.append(c)
    return chosen


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main_export():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-file", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=ROOT /
                    "data" / "demo" / "ragtruth_samples.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-chars", type=int, default=3000,
                    help="only sample examples whose source+response fit this (readable in the UI); never truncated")
    args = ap.parse_args()

    main.load_ragtruth()
    if main.state["mode"] != "model":
        sys.exit(
            f"Real model not loaded from {main.MODEL_DIR}. Aborting (would export mock scores).")

    presets = main.presets()
    thr = presets["Balanced detection"]
    rows = load_examples(args.test_file)
    print(f"Scoring {len(rows)} examples ...")
    for i, r in enumerate(rows):
        r["source_info"] = str(r["source_info"])
        r["probability"] = round(main.score_text(r["task_type"], r["source_info"], r["response"],
                                                 str(r["dataset_name"])), 4)
        pred = r["probability"] >= thr
        truth = bool(int(r["label"]))
        r["category"] = "TP" if pred and truth else "FP" if pred else "FN" if truth else "TN"
        if i % 100 == 0:
            print(f"  {i}/{len(rows)}")

    from sklearn.metrics import precision_recall_fscore_support
    y = [int(r["label"]) for r in rows]
    p = [int(r["probability"] >= thr) for r in rows]
    prec, rec, f1, _ = precision_recall_fscore_support(
        y, p, average="binary", zero_division=0)

    rng = random.Random(args.seed)
    samples = []
    for cat, k in PLAN.items():
        pool = [r for r in rows if r["category"] == cat
                and len(r["source_info"]) + len(r["response"]) <= args.max_chars]
        chosen = pick(pool, k, rng)
        if len(chosen) < k:
            print(
                f"WARNING: only {len(chosen)} {cat} examples available (wanted {k})")
        samples += chosen

    out = {
        "meta": {
            "model": main.state["cfg"].get("selected_model"),
            "checkpoint_sha256": sha256(main.MODEL_DIR / "model.safetensors"),
            "input_mode": main.state["cfg"].get("input_mode"),
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "selection_rule": f"seed={args.seed}; random per outcome category at the 'Balanced detection' "
            f"threshold ({thr}); plan={PLAN}; spread across task types; "
            f"max {args.max_chars} chars. Not hand-picked for impressiveness.",
            "sensitivity_presets": presets,
            "test_metrics_balanced": {"n": len(rows), "precision": round(float(prec), 4),
                                      "recall": round(float(rec), 4), "f1": round(float(f1), 4)},
            "note": "Probabilities were produced by the real trained model at export time. "
                    "The deployed demo serves these stored values; it does not run live inference.",
        },
        "samples": [{
            "id": f"rt-{i + 1:02d}", "category": r["category"],
            "task_type": r["task_type"], "dataset_name": str(r["dataset_name"]),
            "source_info": r["source_info"], "response": r["response"],
            "true_label": int(r["label"]), "probability": r["probability"],
        } for i, r in enumerate(samples)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(samples)} samples to {args.out}")
    print("Metrics:", out["meta"]["test_metrics_balanced"])


if __name__ == "__main__":
    main_export()
