
import json
from pathlib import Path

import mlflow

ROOT = Path(__file__).resolve().parent.parent

mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
mlflow.set_experiment("SentinelAI")


def load_json(path):
    with open(ROOT / path, "r", encoding="utf-8") as file:
        return json.load(file)


def log_engine(name, metadata, metrics=None):
    with mlflow.start_run(run_name=name):
        mlflow.set_tag("engine", name)
        mlflow.set_tag("version", metadata.get("version", "v0.1.0"))

        mlflow.log_dict(metadata, "metadata.json")

        if metrics:
            mlflow.log_metrics(metrics)

        print(f"Logged {name}: {mlflow.active_run().info.run_id}")


# NAB
nab = load_json("models/nab/v0.1.0/metadata.json")
log_engine("NAB", nab)

# SMD
smd = load_json("models/smd/v0.1.0/metadata.json")
log_engine("SMD", smd)

# RAGTruth
rag = load_json("models/ragtruth_metadata.json")
rag_metrics = rag["test_metrics"]

log_engine(
    "RAGTruth",
    rag,
    {
        "accuracy": rag_metrics["accuracy"],
        "precision": rag_metrics["precision"],
        "recall": rag_metrics["recall"],
        "f1": rag_metrics["f1"],
        "pr_auc": rag_metrics["pr_auc"],
        "roc_auc": rag_metrics["roc_auc"],
    },
)

print("\nAll three SentinelAI engines logged successfully!")
