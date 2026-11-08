"""Shrink the RAGTruth model from fp32 (~570 MB) to fp16 (~285 MB) and sanity-check it."""
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SRC = Path("models/ragtruth/v0.1.0/model")
DST = Path("models/ragtruth/v0.1.0/model_fp16")

SAMPLES = [
    ("The Eiffel Tower is in Paris and was completed in 1889.",
     "The Eiffel Tower, finished in 1889, stands in Paris."),
    ("The Eiffel Tower is in Paris and was completed in 1889.",
     "The Eiffel Tower is in Berlin and was built in 1950."),
    ("Water boils at 100 degrees Celsius at sea level.",
     "Water boils at 100 degrees Celsius at sea level."),
]


def size_mb(folder: Path) -> float:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / 1024 / 1024


def logits_for(model, tok, pairs):
    enc = tok([a for a, _ in pairs], [b for _, b in pairs],
              return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        return model(**enc).logits


def main():
    if not SRC.exists():
        raise SystemExit(
            f"Missing {SRC} - run step2_organize_models.ps1 first.")

    print(f"Source size: {size_mb(SRC):.1f} MB")
    tok = AutoTokenizer.from_pretrained(SRC)

    print("Loading fp32 original ...")
    m32 = AutoModelForSequenceClassification.from_pretrained(
        SRC, torch_dtype=torch.float32).eval()

    print("Converting to fp16 and saving ...")
    m16 = AutoModelForSequenceClassification.from_pretrained(
        SRC, torch_dtype=torch.float16)
    DST.mkdir(parents=True, exist_ok=True)
    m16.save_pretrained(DST, safe_serialization=True)
    tok.save_pretrained(DST)
    print(f"fp16 folder size: {size_mb(DST):.1f} MB")

    print("Reloading fp16 weights as fp32 (how the API will load them) ...")
    m16_up = AutoModelForSequenceClassification.from_pretrained(
        DST, torch_dtype=torch.float32).eval()

    a = logits_for(m32, tok, SAMPLES)
    b = logits_for(m16_up, tok, SAMPLES)
    print("\n--- Sanity check (NOT a replacement for your real evaluation) ---")
    print(f"max |logit difference|: {(a - b).abs().max().item():.5f}")
    print(
        f"same predictions on {len(SAMPLES)} samples: {(a.argmax(-1) == b.argmax(-1)).all().item()}")
    print("\nNext: re-run your evaluation on model_fp16 and compare F1 with the fp32 result.")


if __name__ == "__main__":
    main()
