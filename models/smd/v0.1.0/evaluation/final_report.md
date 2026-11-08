# Final Results: Anomaly Detection on SMD (machine-1-1, 1-2, 1-3)

## 1. Exploration summary

1. **Data inspection.** Train, test and labels were explored, and train was compared with test.
2. **Distribution shift.** A threshold derived from train scores flagged far too many test rows (1-1: 60%, 1-3: 69%). Implied true anomaly rates are only 1-1: 9.5%, 1-2: 2.3%, 1-3: 3.4%, so train-derived thresholds are not usable here.
3. **Clipping.** Clipping outliers barely changed results, so the shift is not driven by extreme values.
4. **Baseline OCSVM.** Scores rank anomalies reasonably on 1-1 (ROC-AUC 0.88, PR-AUC 0.56) and less well on 1-2 and 1-3. The main weakness was thresholding, not scoring.
5. **Fix.** The train-based cutoff was replaced by a label-free, fixed top-5% flag rate on test scores.
6. **Model comparison.** OCSVM (nu = 0.01, 0.05) and IsolationForest were compared; the rolling window was considered but not used.

**Internal consistency check.** Precision x flag rate = recall x prevalence, so implied prevalence should be identical across models on one machine. It is (max spread 0.000), so there are no row-level bugs.

## 2. Setup and items to confirm

- Nu and redundancy threshold selected without test labels: **Yes**
- Redundancy threshold: **0.98**
- Scaler fit on train only: **Yes**
- IsolationForest seeds: **single run (seed variance unmeasured)**
- Threshold: top-5% of test scores. Label-free but transductive, and mismatched to true prevalence.

## 3. Final results (headline metrics)

| machine | model | precision | recall | F1 | ROC_AUC | PR_AUC | PR baseline | PR lift (x) | segments_hit |
|---|---|---|---|---|---|---|---|---|---|
| machine-1-1 | OCSVM nu=0.01 | 0.791 | 0.418 | 0.547 | 0.863 | 0.516 | 0.095 | 5.451 | 5/8 |
| machine-1-1 | OCSVM nu=0.05 | 0.748 | 0.395 | 0.517 | 0.867 | 0.508 | 0.095 | 5.367 | 5/8 |
| machine-1-1 | IsolationForest | 0.462 | 0.244 | 0.320 | 0.891 | 0.429 | 0.095 | 4.532 | 5/8 |
| machine-1-2 | OCSVM nu=0.01 | 0.264 | 0.577 | 0.362 | 0.841 | 0.438 | 0.023 | 19.171 | 8/10 |
| machine-1-2 | OCSVM nu=0.05 | 0.269 | 0.589 | 0.369 | 0.864 | 0.426 | 0.023 | 18.645 | 8/10 |
| machine-1-2 | IsolationForest | 0.263 | 0.576 | 0.361 | 0.927 | 0.436 | 0.023 | 19.083 | 8/10 |
| machine-1-3 | OCSVM nu=0.01 | 0.176 | 0.256 | 0.209 | 0.777 | 0.145 | 0.034 | 4.212 | 6/12 |
| machine-1-3 | OCSVM nu=0.05 | 0.171 | 0.248 | 0.203 | 0.785 | 0.146 | 0.034 | 4.241 | 7/12 |
| machine-1-3 | IsolationForest | 0.243 | 0.353 | 0.288 | 0.811 | 0.308 | 0.034 | 8.947 | 9/12 |

*PR lift = PR-AUC / prevalence, i.e. how many times better than random.*

## 4. Findings per machine

- **machine-1-1** (prevalence ~9.5%): best PR-AUC is OCSVM nu=0.01 (0.516, 5.5x baseline); spread across models 0.087 -> clear gap.
- **machine-1-2** (prevalence ~2.3%): best PR-AUC is OCSVM nu=0.01 (0.438, 19.2x baseline); spread across models 0.012 -> no meaningful gap between models.
- **machine-1-3** (prevalence ~3.4%): best PR-AUC is IsolationForest (0.308, 8.9x baseline); spread across models 0.163 -> clear gap.
- **nu = 0.01 vs 0.05:** max PR-AUC difference 0.012; not meaningful, so no claim either is better.
- **Overall:** best model by PR-AUC differs across machines (2 distinct winners over 3 machines), so no overall ranking is claimed.

## 5. Which numbers can be trusted

| Metric | Verdict | Reason |
|---|---|---|
| PR_AUC | TRUST (headline) | Threshold-free and label-free. Read against each machine's prevalence baseline. |
| ROC_AUC | TRUST WITH CAUTION | Label-free ranking check, but inflated under rare anomalies. Disagrees with PR_AUC on 1-1. |
| Precision / Recall / F1 @ top-5% | VALID WITHIN A MACHINE ONLY | Fixed 5% rate is arbitrary and mismatched to prevalence; do not average or compare across machines. |
| segments_hit | TRUST WITH CAUTION | Honest event-level view, but counts are small (8-12). Only the gap on 1-3 looks real. |
| PA_F1 | DO NOT TRUST | Point-adjustment inflates scores (up to +0.55 over F1). Diagnostic only. |
| best_F1_oracle | DO NOT TRUST AS A RESULT | Threshold chosen with test labels: an upper bound (up to +0.17 over F1). Shows headroom only. |
| nu comparison | NOT A FINDING | Differences within noise (max 0.012 PR-AUC). |
| Overall ranking / cross-machine mean | NOT SUPPORTED | Only 3 machines, winners flip, no seeds or confidence intervals. |

## 6. Diagnostic-only table (do not headline)

| machine | model | PA_F1 | PA_inflation | best_F1_oracle | oracle_gap |
|---|---|---|---|---|---|
| machine-1-1 | OCSVM nu=0.01 | 0.946 | 0.399 | 0.549 | 0.002 |
| machine-1-1 | OCSVM nu=0.05 | 0.936 | 0.419 | 0.556 | 0.039 |
| machine-1-1 | IsolationForest | 0.874 | 0.554 | 0.495 | 0.175 |
| machine-1-2 | OCSVM nu=0.01 | 0.548 | 0.186 | 0.471 | 0.109 |
| machine-1-2 | OCSVM nu=0.05 | 0.550 | 0.181 | 0.465 | 0.096 |
| machine-1-2 | IsolationForest | 0.548 | 0.187 | 0.489 | 0.128 |
| machine-1-3 | OCSVM nu=0.01 | 0.547 | 0.338 | 0.229 | 0.020 |
| machine-1-3 | OCSVM nu=0.05 | 0.571 | 0.368 | 0.236 | 0.033 |
| machine-1-3 | IsolationForest | 0.607 | 0.319 | 0.315 | 0.027 |

## 7. Caveats

- Single run: unmeasured seed variance, especially for IsolationForest.
- Top-5% cutoff is transductive (computed on test scores).
- Three machines is too few for general claims about model quality.
- Near-identical 1-2 results across three models suggest the same dominant segments are flagged; verify with an overlap check on flagged indices.
