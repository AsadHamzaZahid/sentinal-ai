
# SMD Anomaly Detection: Methodology

## Dataset
Three machines were selected:
- machine-1-1
- machine-1-2
- machine-1-3

The complete SMD dataset contains 28 machines.
Results from this experiment should not be generalized
to all machines.

## Models
- One-Class SVM (nu=0.01)
- One-Class SVM (nu=0.05)
- Isolation Forest

## Preprocessing
- Constant training metrics removed.
- Redundant features removed using training correlations.
- StandardScaler fitted on training data only.
- Extreme scaled values clipped at +/-10 for model fitting.

## Evaluation
The fixed top-5% threshold is calculated from test scores.
It is label-free, but uses the test distribution.
It is therefore transductive and not a deployable threshold.

PR-AUC and ROC-AUC evaluate score ranking.
Precision, recall and F1 use the fixed alert budget.
Point-adjusted F1 and oracle F1 are diagnostic only.

## Limitations
- Only three of 28 machines were evaluated.
- Isolation Forest stability was assessed across five seeds.
- Results are dataset-specific.
- No production-ready threshold calibration is claimed.
