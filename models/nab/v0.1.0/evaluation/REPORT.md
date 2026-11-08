# Anomaly detection baseline: evaluation report (NAB, 9 files)

## Method
- Features: value plus past-only rolling mean/std (12 and 72 rows), diff, short z-score, long deviation. Labels are never used as features.
- Per file, chronological segments: fit (first 15%, capped at half the clean prefix), validation (next 15%, anomaly-free), test (the rest).
- Threshold: set on validation scores so validation false-alarm rate is 0.5% of rows. Test labels are not used for thresholds.
- Design per file: fixed fit, or trailing-window refit (1440 rows) if the fixed model flags >2% of validation rows (label-free drift rule).
- All designs scored identical test rows (asserted in code).

## Splits
                                    file  fit_end  val_end  val_rows  test_rows  test_anom_rows  windows_in_test  windows_crossing  val_drift_rate chosen
                 art_daily_jumpsdown.csv      604     1208       604       2824             403                1                 0           0.002  fixed
                   art_daily_jumpsup.csv      604     1208       604       2824             403                1                 0           0.007  fixed
               art_daily_small_noise.csv      604     1208       604       2824               0                0                 0           0.003  fixed
cpu_utilization_asg_misconfiguration.csv     2707     5414      2707      12636            1499                1                 0           0.011  fixed
          ec2_cpu_utilization_5f5533.csv      585     1171       586       2861             402                2                 0           0.002  fixed
         ec2_disk_write_bytes_1ef3de.csv      709     1418       709       3312             473                1                 0           0.013  fixed
               ec2_network_in_5abac7.csv      709     1418       709       3312             474                2                 0           0.010  fixed
  ec2_request_latency_system_failure.csv      604     1208       604       2824             346                3                 0           0.026  W1440
  machine_temperature_system_failure.csv     1063     2126      1063      20569            2268                4                 0           0.009  fixed

## Final results (selected design per file)
                                    file design  threshold  precision  recall    f1  false_alarm_rate  false_alarms_per_day  windows  detected  mean_lag_frac  flagged_pct
                 art_daily_jumpsdown.csv  fixed    -0.0144      0.062   0.002 0.005            0.0062                  1.78        1         1           0.05         0.57
                   art_daily_jumpsup.csv  fixed     0.0025      0.143   0.005 0.010            0.0050                  1.43        1         1           0.50         0.50
               art_daily_small_noise.csv  fixed    -0.0037        NaN     NaN   NaN            0.0060                  1.73        0         0            NaN         0.60
cpu_utilization_asg_misconfiguration.csv  fixed     0.0159      0.412   0.081 0.135            0.0155                  4.47        1         1           0.01         2.33
          ec2_cpu_utilization_5f5533.csv  fixed    -0.0152      0.095   0.522 0.161            0.8150                234.71        2         2           0.12        77.39
         ec2_disk_write_bytes_1ef3de.csv  fixed     0.0140      0.174   0.017 0.031            0.0134                  3.85        1         1           0.36         1.39
               ec2_network_in_5abac7.csv  fixed     0.0140      0.333   0.017 0.032            0.0056                  1.62        2         2           0.25         0.72
  ec2_request_latency_system_failure.csv  W1440     0.0419      0.571   0.012 0.023            0.0012                  0.35        3         2           0.50         0.25
  machine_temperature_system_failure.csv  fixed     0.0097      0.531   0.042 0.078            0.0046                  1.32        4         4           0.37         0.87

## All designs (information only)
                                    file design  threshold  precision  recall    f1  false_alarm_rate  false_alarms_per_day  windows  detected  mean_lag_frac  flagged_pct
                 art_daily_jumpsdown.csv  fixed    -0.0144      0.062   0.002 0.005            0.0062                  1.78        1         1           0.05         0.57
                 art_daily_jumpsdown.csv   W576    -0.0241      0.024   0.002 0.005            0.0165                  4.76        1         1           0.05         1.45
                 art_daily_jumpsdown.csv  W1440    -0.0250      0.040   0.002 0.005            0.0099                  2.86        1         1           0.05         0.89
                   art_daily_jumpsup.csv  fixed     0.0025      0.143   0.005 0.010            0.0050                  1.43        1         1           0.50         0.50
                   art_daily_jumpsup.csv   W576     0.0039      0.231   0.007 0.014            0.0041                  1.19        1         1           0.05         0.46
                   art_daily_jumpsup.csv  W1440    -0.0022      0.364   0.010 0.019            0.0029                  0.83        1         1           0.05         0.39
               art_daily_small_noise.csv  fixed    -0.0037        NaN     NaN   NaN            0.0060                  1.73        0         0            NaN         0.60
               art_daily_small_noise.csv   W576    -0.0084        NaN     NaN   NaN            0.0060                  1.73        0         0            NaN         0.60
               art_daily_small_noise.csv  W1440    -0.0086        NaN     NaN   NaN            0.0071                  2.04        0         0            NaN         0.71
cpu_utilization_asg_misconfiguration.csv  fixed     0.0159      0.412   0.081 0.135            0.0155                  4.47        1         1           0.01         2.33
cpu_utilization_asg_misconfiguration.csv   W576     0.0602      0.000   0.000 0.000            0.0020                  0.57        1         0            NaN         0.17
cpu_utilization_asg_misconfiguration.csv  W1440     0.0237      0.029   0.001 0.003            0.0059                  1.71        1         1           0.17         0.54
          ec2_cpu_utilization_5f5533.csv  fixed    -0.0152      0.095   0.522 0.161            0.8150                234.71        2         2           0.12        77.39
          ec2_cpu_utilization_5f5533.csv   W576    -0.0120      0.381   0.311 0.342            0.0826                 23.78        2         2           0.02        11.46
          ec2_cpu_utilization_5f5533.csv  W1440    -0.0164      0.236   0.095 0.135            0.0500                 14.41        2         2           0.46         5.63
         ec2_disk_write_bytes_1ef3de.csv  fixed     0.0140      0.174   0.017 0.031            0.0134                  3.85        1         1           0.36         1.39
         ec2_disk_write_bytes_1ef3de.csv   W576     0.0111      0.551   0.091 0.156            0.0123                  3.55        1         1           0.29         2.36
         ec2_disk_write_bytes_1ef3de.csv  W1440     0.0148      0.250   0.011 0.020            0.0053                  1.52        1         1           0.44         0.60
               ec2_network_in_5abac7.csv  fixed     0.0140      0.333   0.017 0.032            0.0056                  1.62        2         2           0.25         0.72
               ec2_network_in_5abac7.csv   W576     0.0106      0.784   0.061 0.114            0.0028                  0.81        2         1           0.19         1.12
               ec2_network_in_5abac7.csv  W1440     0.0034      0.684   0.027 0.053            0.0021                  0.61        2         2           0.25         0.57
  ec2_request_latency_system_failure.csv  fixed     0.0325      0.325   0.072 0.118            0.0210                  6.04        3         3           0.37         2.73
  ec2_request_latency_system_failure.csv   W576     0.0368      0.500   0.012 0.023            0.0016                  0.46        3         2           0.37         0.28
  ec2_request_latency_system_failure.csv  W1440     0.0419      0.571   0.012 0.023            0.0012                  0.35        3         2           0.50         0.25
  machine_temperature_system_failure.csv  fixed     0.0097      0.531   0.042 0.078            0.0046                  1.32        4         4           0.37         0.87
  machine_temperature_system_failure.csv   W576     0.0521      0.365   0.057 0.098            0.0122                  3.53        4         2           0.50         1.72
  machine_temperature_system_failure.csv  W1440     0.0004      0.249   0.052 0.085            0.0193                  5.56        4         3           0.47         2.28

## Limitations

- One model family (IsolationForest), one seed, no second model for comparison.
- Nine files with 0-4 anomaly windows each. One missed window is a quarter or a third of a file's evidence, and no confidence intervals are given. Per-file results are anecdotal.
- Row-level precision/recall/F1 are pessimistic. NAB windows span about 10% of a file, and a detector that fires on a few rows inside a window scores low recall. Window detection and lag are reported beside them; this is not the NAB score.
- Split points use label positions (the first anomaly) to guarantee a clean fit and validation period. A deployed system would not know where anomalies start, so thresholds here are calibrated on cleaner data than in practice.
- Validation is short (about 2-9 days). Drift beyond it is not covered by the threshold.
- The design-selection rule and its 2% drift cut-off are my choices and were not tuned or sensitivity-tested.
- Earlier diagnostics (feature ablation, drift analysis) looked at labelled test-period data, and they informed which designs and features were tried. Test numbers are therefore not fully untouched.
- Duplicate timestamps were kept. Three ec2 files have 12 rows stamped 2014-03-09 03:00 (a daylight-saving collapse, confirmed by the gap around it). machine_temperature repeats the 02:00-02:55 hour on 2014-01-07 for an unknown reason. Features are row-based, so neither matters for the features, but any time-based feature would be wrong.
- art_daily_* files are synthetic, and art_daily_small_noise has no anomalies, so it only measures false alarms.
- For walk-forward designs the saved model is the last refit, not a single model. The procedure in the config is what to re-run.



## Interpretation
                                    file design  base_rate  precision  lift  flagged_rows  tp_rows  false_alarm_rate  detected  windows  chance_hit_prob                       verdict
                 art_daily_jumpsdown.csv  fixed      0.143      0.062  0.43            16      1.0            0.0062         1        1             0.91 indistinguishable from chance
                   art_daily_jumpsup.csv  fixed      0.143      0.143  1.00            14      2.0            0.0050         1        1             0.88 indistinguishable from chance
               art_daily_small_noise.csv  fixed      0.000        NaN   NaN            17      NaN            0.0060         0        0              NaN   control (false alarms only)
cpu_utilization_asg_misconfiguration.csv  fixed      0.119      0.412  3.46           294    121.0            0.0155         1        1             1.00                      credible
          ec2_cpu_utilization_5f5533.csv  fixed      0.141      0.095  0.67          2214    210.0            0.8150         2        2             1.00          FAILED (alarm flood)
         ec2_disk_write_bytes_1ef3de.csv  fixed      0.143      0.174  1.22            46      8.0            0.0134         1        1             1.00 indistinguishable from chance
               ec2_network_in_5abac7.csv  fixed      0.143      0.333  2.33            24      8.0            0.0056         2        2             0.83 suggestive (few flagged rows)
  ec2_request_latency_system_failure.csv  W1440      0.123      0.571  4.64             7      4.0            0.0012         2        3             0.25 suggestive (few flagged rows)
  machine_temperature_system_failure.csv  fixed      0.110      0.531  4.83           179     95.0            0.0046         4        4             0.99                      credible

- Verdict rule (fixed before reading results): control if no windows; FAILED if test false-alarm rate > 5%; chance-level if precision < 1.5x the test base rate; suggestive if fewer than 30 rows flagged; otherwise credible.
- chance_hit_prob is the probability that the same number of randomly placed flags would hit a given window. "Detected" counts mean little where it is high.
- ec2_cpu_utilization failed: the drift rule saw no drift in validation (0.002), but the level shift occurs after validation and the fixed model then flagged 77% of the test period. The selection was not changed afterwards.
- ec2_request_latency was routed to W1440 by a narrow margin (0.026 vs 0.02), and its result rests on about 7 flagged rows.
- Only machine_temperature and cpu_utilization_asg show clear skill. The art_daily_* files, ec2_disk_write_bytes and ec2_cpu_utilization should not be reported as successes.
- At the 0.5% validation target, false alarms are about 1.4 per day on 5-minute data, which is noisy for operational use.
- Row-level recall is below 0.09 on every file because detections are brief inside wide windows.
