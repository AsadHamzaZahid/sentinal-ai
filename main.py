"""SentinelAI API (RAGTruth + NAB + SMD).  Run from the project root:  uvicorn main:app --reload

RAGTruth modes (env RAGTRUTH_MODE = live | precomputed | auto, default auto):
  live         load the trained ModernBERT model (needs torch + transformers, see requirements-live.txt)
  precomputed  serve stored predictions from data/demo/ragtruth_samples.json (no torch, light deployment)
  auto         live if the model files exist, otherwise precomputed if the samples file exists, otherwise mock
NAB and SMD are unchanged. Every engine falls back gracefully if its files are missing."""
import ast
import json
import logging
import os
import time
import warnings
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
MODELS = Path(os.getenv("SENTINEL_MODELS_DIR", ROOT / "models"))
MODEL_DIR = Path(os.getenv("SENTINEL_MODEL_DIR", MODELS /
                 "ragtruth" / "v0.1.0" / "model_fp16"))
SMD_DIR = Path(os.getenv("SENTINEL_SMD_DIR", MODELS / "smd" / "v0.1.0"))
SMD_DATA = ROOT / "OmniAnomaly-master" / "ServerMachineDataset"
NAB_DIR = ROOT / "NAB_outputs" / "prepared"
# thresholds + manifest written by scripts/build_artifacts.py
ARTIFACTS = ROOT / "artifacts"
# precomputed RAGTruth predictions written by scripts/export_ragtruth_samples.py
RAG_SAMPLES = Path(os.getenv("SENTINEL_RAG_SAMPLES",
                   ROOT / "data" / "demo" / "ragtruth_samples.json"))
RAGTRUTH_MODE = os.getenv("RAGTRUTH_MODE", "auto").lower()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentinelai")

TASKS = {"Summary", "QA", "Data2txt"}
DEFAULT_PRESETS = {"Catch as many as possible": 0.25,
                   "Balanced detection": 0.31, "Only flag stronger signals": 0.51}

# mode: "model" (live) | "precomputed" | "mock"
state = {"mode": "mock", "cfg": {}, "tok": None, "model": None, "device": "cpu",
         "samples": [], "samples_meta": {}}
# loaded joblib bundles + calibrated thresholds
smd = {"bundles": {}, "cache": {}}
alerts: deque = deque(maxlen=200)


# ---------------------------------------------------------------- alerts
def push_alert(source: str, score: float, threshold: float, message: str):
    ratio = score / threshold if threshold else 1.0
    severity = "high" if ratio >= 2 else "medium" if ratio >= 1.3 else "low"
    alerts.appendleft({"id": len(alerts) and alerts[0]["id"] + 1 or 1, "source": source, "severity": severity,
                       "score": round(float(score), 4), "message": message,
                       "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")})


# ---------------------------------------------------------------- startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_ragtruth()
    load_smd()
    load_thresholds()
    yield


app = FastAPI(title="SentinelAI", version="2.2", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("%s %s failed", request.method, request.url.path)
        raise
    log.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


def load_ragtruth_samples():
    if RAG_SAMPLES.exists():
        data = json.loads(RAG_SAMPLES.read_text(encoding="utf-8"))
        state["samples"] = data.get("samples", [])
        state["samples_meta"] = data.get("meta", {})
        log.info("[RAGTruth] Loaded %d precomputed samples",
                 len(state["samples"]))


def load_ragtruth():
    load_ragtruth_samples()
    cfg_path = next((p for p in (MODEL_DIR / "sentinel_config.json",
                    MODEL_DIR.parent / "sentinel_config.json",
                    ROOT / "sentinel_config.json") if p.exists()), None)
    model_ok = bool(cfg_path and (MODEL_DIR / "config.json").exists())

    if RAGTRUTH_MODE in ("live", "auto") and model_ok:
        import torch  # only imported in live mode, so deployments never need it
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        state["cfg"] = json.loads(cfg_path.read_text())
        state["tok"] = AutoTokenizer.from_pretrained(MODEL_DIR)
        # low-memory servers: keep weights in bfloat16 (half the RAM of float32)
        dtype = torch.bfloat16 if os.getenv(
            "SENTINEL_LOW_MEMORY") == "1" else torch.float32
        state["model"] = AutoModelForSequenceClassification.from_pretrained(
            MODEL_DIR, dtype=dtype).eval()
        state["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        state["model"].to(state["device"])
        state["mode"] = "model"
        print(
            f"[RAGTruth] Loaded {state['cfg'].get('selected_model')} on {state['device']} ({dtype}).")
        return

    if RAGTRUTH_MODE == "mock":
        state["cfg"] = {"sensitivity_presets": DEFAULT_PRESETS}
        state["mode"] = "mock"
        print("[RAGTruth] MOCK mode (forced by configuration).")
        return

    if RAGTRUTH_MODE == "live":
        log.warning(
            "[RAGTruth] RAGTRUTH_MODE=live but no model in '%s'; falling back.", MODEL_DIR)
    if state["samples"]:
        meta = state["samples_meta"]
        state["cfg"] = {"selected_model": meta.get("model"),
                        "sensitivity_presets": meta.get("sensitivity_presets", DEFAULT_PRESETS)}
        state["mode"] = "precomputed"
        print("[RAGTruth] PRECOMPUTED demo mode (no live model).")
    else:
        print(
            f"[RAGTruth] No model in '{MODEL_DIR}' and no samples file. MOCK mode.")


def load_smd():
    import joblib
    for f in sorted(SMD_DIR.glob("machine-*_models.joblib")):
        name = f.name.replace("_models.joblib", "")
        try:
            with warnings.catch_warnings():
                # sklearn version-mismatch warnings
                warnings.simplefilter("ignore")
                b = joblib.load(f)
            models = b["models"]
            if not isinstance(models, dict):
                models = {getattr(m, "__class__").__name__ +
                          f"_{i}": m for i, m in enumerate(models)}
            smd["bundles"][name] = {
                "features": b["features"], "scaler": b["scaler"], "models": models}
            print(f"[SMD] Loaded {name}: models={list(models)}")
        except Exception as e:
            print(f"[SMD] Could not load {f.name}: {e}")


# ---------------------------------------------------------------- RAGTruth engine
def source_to_text(x) -> str:
    if isinstance(x, (list, dict)):
        val = x
    else:
        try:
            val = ast.literal_eval(x)
        except Exception:
            return str(x)
    if isinstance(val, list):
        return " ".join(map(str, val))
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


def presets() -> dict:
    return state["cfg"].get("sensitivity_presets", DEFAULT_PRESETS)


def score_text(task: str, source: str, response: str, dataset: str) -> float:
    if state["mode"] == "mock":
        src_words = set(source_to_text(source).lower().split())
        words = response.lower().split()
        return round(min(0.98, 0.1 + 0.9 * sum(w not in src_words for w in words) / max(1, len(words))), 4)
    import torch
    cfg = state["cfg"]
    first = (f"Task: {task}. Source: {source_to_text(source)}" if cfg["input_mode"] == "source_aware"
             else f"{task} to {dataset}")
    enc = state["tok"](first, response, truncation="longest_first", max_length=cfg["max_length"],
                       return_tensors="pt").to(state["device"])
    with torch.no_grad():
        logits = state["model"](**enc).logits.float()
    return float(torch.softmax(torch.nan_to_num(logits), dim=-1)[0, 1])


class PredictIn(BaseModel):
    task_type: str = Field(..., examples=["Summary"])
    source_info: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    dataset_name: str = ""
    sensitivity_mode: str = "Balanced detection"
    sample_id: Optional[str] = None  # used by the precomputed demo


def find_sample(item: PredictIn) -> Optional[dict]:
    if item.sample_id:
        s = next((s for s in state["samples"]
                 if s["id"] == item.sample_id), None)
        if s is None:
            raise HTTPException(404, f"Unknown sample_id '{item.sample_id}'")
        return s

    def norm(t):
        return " ".join(t.split())
    return next((s for s in state["samples"]
                 if s["task_type"] == item.task_type
                 and norm(s["source_info"]) == norm(item.source_info)
                 and norm(s["response"]) == norm(item.response)), None)


def predict_one(item: PredictIn) -> dict:
    if item.task_type not in TASKS:
        raise HTTPException(422, f"task_type must be one of {sorted(TASKS)}")
    if item.sensitivity_mode not in presets():
        raise HTTPException(
            422, f"sensitivity_mode must be one of {list(presets())}")
    sample = None
    if state["mode"] == "precomputed":
        sample = find_sample(item)
        if sample is None:
            raise HTTPException(422, "This deployment is a precomputed demo: live scoring is disabled. "
                                     "Select one of the provided samples (GET /ragtruth/samples).")
        prob = float(sample["probability"])
    else:
        prob = score_text(item.task_type, item.source_info,
                          item.response, item.dataset_name)
    thr = presets()[item.sensitivity_mode]
    flagged = prob >= thr
    if flagged:
        push_alert("hallucination", prob, thr,
                   f"{item.task_type} response likely hallucinated ({prob:.0%})")
    out = {"hallucinated": flagged, "probability": round(prob, 4), "threshold": thr,
           "sensitivity_mode": item.sensitivity_mode, "engine": state["mode"],
           "precomputed": state["mode"] == "precomputed"}
    if sample:
        out["sample"] = {"id": sample["id"], "true_label": sample["true_label"],
                         "category": sample["category"]}
    return out


# ---------------------------------------------------------------- SMD engine
def _raw_score(est, Z):
    """Higher = more anomalous, for IsolationForest / OneClassSVM."""
    if hasattr(est, "score_samples"):
        return -est.score_samples(Z)
    return -est.decision_function(Z)


def _select(X: np.ndarray, feats) -> np.ndarray:
    # names like "metric_5" -> column 5 of the 38
    if all(isinstance(f, str) for f in feats):
        idx = [int(f.rsplit("_", 1)[1]) for f in feats]
        if X.shape[1] <= max(idx):
            raise HTTPException(
                422, f"Rows need at least {max(idx) + 1} columns (SMD rows have 38)")
        return X[:, idx]
    try:
        if all(isinstance(f, (int, np.integer)) for f in feats):
            return X[:, list(feats)]
    except IndexError:
        raise HTTPException(
            422, f"Rows need at least {max(feats) + 1} columns")
    if X.shape[1] == len(feats):
        return X
    raise HTTPException(
        422, f"Rows must have {len(feats)} columns (the model's features)")


def _pick_model(b: dict, model: Optional[str]) -> str:
    names = list(b["models"])
    if model:
        if model not in b["models"]:
            raise HTTPException(422, f"model must be one of {names}")
        return model
    return next((n for n in names if "nu_001" in n or "0.01" in n), names[0])


def smd_scores(machine: str, model: Optional[str], X: np.ndarray):
    if machine not in smd["bundles"]:
        raise HTTPException(
            404, f"Unknown machine. Available: {sorted(smd['bundles'])}")
    b = smd["bundles"][machine]
    mname = _pick_model(b, model)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Z = b["scaler"].transform(_select(X, b["features"]))
        return _raw_score(b["models"][mname], np.nan_to_num(Z)), Z, mname


def _load_txt(kind: str, machine: str):
    p = SMD_DATA / kind / f"{machine}.txt"
    return np.loadtxt(p, delimiter=",") if p.exists() else None


def load_thresholds():
    """Use saved thresholds (artifacts/smd_thresholds.json) so SMD needs no dataset folder at run time."""
    f = ARTIFACTS / "smd_thresholds.json"
    if f.exists():
        for k, v in json.loads(f.read_text()).items():
            machine, mname = k.split("|")
            smd["cache"][(machine, mname)] = float(v)
        log.info("[SMD] Loaded %d saved thresholds", len(smd["cache"]))


def manifest() -> dict:
    f = ARTIFACTS / "manifest.json"
    return json.loads(f.read_text()) if f.exists() else {}


def smd_threshold(machine: str, mname: str, recalibrate: bool = False) -> float:
    """Your reports flag the top 5% of test scores, so use that rule (on a subsample for speed).
    Falls back to the 99th percentile of training scores if test data isn't on disk."""
    key = (machine, mname)
    if recalibrate or key not in smd["cache"]:
        test = _load_txt("test", machine)
        if test is not None:
            s, _, _ = smd_scores(
                machine, mname, test[:: max(1, len(test) // 5000)])
            thr = float(np.percentile(s, 95))
        else:
            train = _load_txt("train", machine)
            if train is None:
                raise HTTPException(
                    500, "No test/train data found to calibrate a threshold")
            s, _, _ = smd_scores(
                machine, mname, train[:: max(1, len(train) // 5000)])
            thr = float(np.percentile(s, 99))
        smd["cache"][key] = thr
    return smd["cache"][key]


class SMDIn(BaseModel):
    machine: str = "machine-1-1"
    model: Optional[str] = None
    rows: List[List[float]] = Field(..., min_length=1, max_length=2000)


# ---------------------------------------------------------------- NAB engine
def robust_z(values: np.ndarray, window: int = 48) -> np.ndarray:
    """Rolling median/MAD z-score using only past points (streaming-safe)."""
    out = np.zeros(len(values))
    for i in range(len(values)):
        w = values[max(0, i - window):i]
        if len(w) < 8:
            continue
        med = np.median(w)
        mad = np.median(np.abs(w - med)) * 1.4826 or (np.std(w) + 1e-9)
        out[i] = abs(values[i] - med) / mad
    return out


class NABIn(BaseModel):
    values: List[float] = Field(..., min_length=10, max_length=20000)
    window: int = Field(48, ge=8, le=1000)
    threshold: float = 4.0


def nab_files() -> dict:
    return {p.stem.replace("scored_", ""): p for p in sorted(NAB_DIR.glob("scored_*.csv"))}


def _downsample(n: int, cap: int = 1500):
    step = max(1, n // cap)
    return slice(None, None, step)


# ---------------------------------------------------------------- routes
@app.get("/health")
def health():
    return {"status": "ok",
            "engines": {"ragtruth": state["mode"], "smd": f"{len(smd['bundles'])} machines" if smd["bundles"] else "unavailable",
                        "nab": f"{len(nab_files())} series" if nab_files() else "live detector only"},
            "model": state["cfg"].get("selected_model"), "device": state["device"],
            "artifacts_built": manifest().get("created_at")}


@app.get("/modes")
def modes():
    pre = state["mode"] == "precomputed"
    return {"modes": presets(), "tasks": sorted(TASKS), "engine": state["mode"],
            "precomputed": pre, "free_text": not pre,
            "notice": ("Pre-computed demo: this deployment does not run the ModernBERT model live. "
                       "Pick one of the samples below. Their scores come from the trained model, "
                       "computed offline.") if pre else None}


@app.get("/ragtruth/samples")
def ragtruth_samples():
    return {"engine": state["mode"], "precomputed": state["mode"] == "precomputed",
            "meta": state["samples_meta"], "samples": state["samples"]}


@app.post("/predict")
def predict(item: PredictIn):
    return predict_one(item)


@app.post("/predict/batch")
def predict_batch(items: List[PredictIn]):
    if len(items) > 50:
        raise HTTPException(422, "Send at most 50 items per request")
    return [predict_one(i) for i in items]


@app.get("/smd/machines")
def smd_machines():
    return {name: list(b["models"]) for name, b in smd["bundles"].items()}


@app.post("/predict/smd")
def predict_smd(item: SMDIn):
    X = np.array(item.rows, dtype=float)
    s, Z, mname = smd_scores(item.machine, item.model, X)
    thr = smd_threshold(item.machine, mname)
    flags = s >= thr
    worst = int(np.argmax(s))
    top = np.argsort(-np.abs(Z[worst]))[:3]
    if flags.any():
        push_alert("smd", s[worst], thr, f"{item.machine}: {int(flags.sum())} abnormal row(s) of {len(s)}, "
                   f"top metrics {', '.join(smd['bundles'][item.machine]['features'][int(t)] for t in top)}")
    return {"machine": item.machine, "model": mname, "threshold": thr, "scores": np.round(s, 4).tolist(),
            "flags": flags.tolist(), "anomalous_rows": int(flags.sum()),
            "top_metrics": [{"metric": smd["bundles"][item.machine]["features"][int(t)], "z": round(float(Z[worst][t]), 2)} for t in top]}


@app.get("/smd/demo")
def smd_demo(machine: str = "machine-1-1", model: Optional[str] = None, start: int = 0, length: int = 1500):
    test = _load_txt("test", machine)
    if test is None:
        raise HTTPException(
            404, f"Test data for {machine} not found in {SMD_DATA}")
    length = min(max(length, 50), 3000)
    start = max(0, min(start, len(test) - length))
    X = test[start:start + length]
    s, Z, mname = smd_scores(machine, model, X)
    thr = smd_threshold(machine, mname)
    lab = _load_txt("test_label", machine)
    labels = lab[start:start +
                 length].astype(int).tolist() if lab is not None else None
    flags = s >= thr
    if flags.any():
        w = int(np.argmax(s))
        push_alert("smd", s[w], thr, f"{machine} replay rows {start}-{start + length}: {int(flags.sum())} abnormal "
                   f"(peak at row {start + w}, top metric {smd['bundles'][machine]['features'][int(np.argmax(np.abs(Z[w])))]})")
    return {"machine": machine, "model": mname, "models": list(smd["bundles"][machine]["models"]), "start": start,
            "total_rows": len(test), "threshold": thr, "scores": np.round(s, 4).tolist(),
            "flags": flags.tolist(), "labels": labels}


@app.get("/nab/series")
def nab_series():
    return {"series": list(nab_files())}


@app.get("/nab/replay")
def nab_replay(name: str):
    import pandas as pd
    files = nab_files()
    if name not in files:
        raise HTTPException(404, f"Unknown series. Available: {list(files)}")
    df = pd.read_csv(files[name])
    low = {c: c.lower() for c in df.columns}
    ts_c = next((c for c in df.columns if "time" in low[c]), None)
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    val_c = next((c for c in num if low[c] == "value"), next(
        (c for c in num if "score" not in low[c] and "label" not in low[c]), None))
    sc_c = next((c for c in num if "score" in low[c]), None)
    lab_c = next((c for c in num if "label" in low[c]), None)
    if val_c is None:
        raise HTTPException(
            500, f"No numeric value column in {files[name].name}: columns={list(df.columns)}")
    values = df[val_c].astype(float).to_numpy()
    scores = df[sc_c].astype(float).to_numpy() if sc_c else robust_z(values)
    scores = np.nan_to_num(scores)
    thr = float(np.percentile(scores, 99))
    flags = scores >= thr
    ds = _downsample(len(values))
    if flags.any():
        push_alert("nab", scores.max(
        ), thr, f"{name}: {int(flags.sum())} unusual points (peak score {scores.max():.2f})")
    return {"name": name, "columns": list(df.columns), "score_source": sc_c or "rolling robust z-score",
            "threshold": thr, "timestamps": df[ts_c].astype(str).tolist()[ds] if ts_c else None,
            "values": np.round(values[ds], 4).tolist(), "scores": np.round(scores[ds], 4).tolist(),
            "flags": flags[ds].tolist(), "labels": df[lab_c].astype(int).to_numpy()[ds].tolist() if lab_c else None}


@app.post("/predict/nab")
def predict_nab(item: NABIn):
    v = np.array(item.values)
    z = robust_z(v, item.window)
    flags = z >= item.threshold
    if flags[-1]:
        push_alert("nab", z[-1], item.threshold,
                   f"Latest metric value {v[-1]:.2f} is unusual (z={z[-1]:.1f})")
    return {"scores": np.round(z, 3).tolist(), "flags": flags.tolist(), "threshold": item.threshold,
            "anomalous_points": int(flags.sum())}


@app.get("/alerts")
def get_alerts(limit: int = 50):
    return list(alerts)[:limit]


@app.delete("/alerts")
def clear_alerts():
    alerts.clear()
    return {"cleared": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
