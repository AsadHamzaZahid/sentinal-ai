"""Build deployment artifacts. Run once from the project root after training/copying models:

    python scripts/build_artifacts.py

Writes:
  artifacts/smd_thresholds.json   flag threshold for every SMD machine + model (so no dataset is needed at run time)
  artifacts/manifest.json         sha256 + size of every model file, library versions, build time
Re-run whenever a model file changes."""
import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
import main  # noqa: E402  (reuses the exact scoring code the API uses)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def version(pkg: str):
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def main_build():
    main.ARTIFACTS.mkdir(exist_ok=True)
    main.load_smd()
    if not main.smd["bundles"]:
        sys.exit("No SMD models found in smd_outputs/. Nothing to build.")

    thresholds = {}
    for machine, b in main.smd["bundles"].items():
        for mname in b["models"]:
            thr = main.smd_threshold(machine, mname, recalibrate=True)
            thresholds[f"{machine}|{mname}"] = thr
            print(f"{machine:12s} {mname:18s} threshold = {thr:.5f}")
    (main.ARTIFACTS / "smd_thresholds.json").write_text(json.dumps(thresholds, indent=2))

    tracked = sorted(main.SMD_DIR.glob("*.joblib"))
    for name in ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "sentinel_config.json"):
        for base in (main.MODEL_DIR, main.ROOT):
            if (base / name).exists():
                tracked.append(base / name)
                break
    files = {}
    for p in tracked:
        print(f"hashing {p.name} ...")
        files[str(p.relative_to(main.ROOT))] = {
            "sha256": sha256(p), "bytes": p.stat().st_size}

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "smd_threshold_rule": "95th percentile of test scores (subsampled to ~5000 rows); 99th percentile of train scores if no test data",
        "libraries": {k: version(k) for k in ("scikit-learn", "numpy", "pandas", "joblib", "torch", "transformers", "fastapi")},
        "files": files,
    }
    (main.ARTIFACTS / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        f"\nWrote {len(thresholds)} thresholds and a manifest for {len(files)} files to {main.ARTIFACTS}")


if __name__ == "__main__":
    main_build()
