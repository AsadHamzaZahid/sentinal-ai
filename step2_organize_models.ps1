# SentinelAI - MLOps Step 2: organise model artifacts
# Run from project root:
#   powershell -ExecutionPolicy Bypass -File .\step2_organize_models.ps1
# COPIES files (originals untouched, main.py keeps working). Safe to re-run.

$ErrorActionPreference = "Continue"
$root = (Get-Location).Path
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$version = "v0.1.0"

function Save-Text($relPath, $text) {
    $full = Join-Path $root $relPath
    $dir = Split-Path $full -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($full, $text, $utf8NoBom)
}

function Remove-Bom($full) {
    if (-not (Test-Path $full)) { return }
    $bytes = [System.IO.File]::ReadAllBytes($full)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        [System.IO.File]::WriteAllBytes($full, $bytes[3..($bytes.Length-1)])
        Write-Host "  BOM removed: $($full.Substring($root.Length+1))" -ForegroundColor Green
    }
}

function Copy-Files($relFiles, $destRel) {
    $dest = Join-Path $root $destRel
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    foreach ($f in $relFiles) {
        $src = Join-Path $root $f
        if (Test-Path $src) {
            Copy-Item $src $dest -Force
            Write-Host "  copied  $f  ->  $destRel" -ForegroundColor Green
        } else {
            Write-Host "  MISSING $f" -ForegroundColor Yellow
        }
    }
}

function Get-Manifest($dirRel) {
    $dir = Join-Path $root $dirRel
    $items = @()
    Get-ChildItem $dir -Recurse -File | Where-Object { $_.Name -ne "metadata.json" } | ForEach-Object {
        $items += [ordered]@{
            path    = $_.FullName.Substring($dir.Length + 1).Replace("\", "/")
            size_mb = [math]::Round($_.Length / 1MB, 2)
            sha256  = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        }
    }
    return $items
}

function Read-Json($rel) {
    $full = Join-Path $root $rel
    if (Test-Path $full) { return (Get-Content $full -Raw | ConvertFrom-Json) }
    return $null
}

# ---------------------------------------------------------------
Write-Host "`n[0/5] Fixing BOM in files created by step 1 ..." -ForegroundColor Yellow
@(".gitignore", "pyproject.toml", ".env.example", "configs\models.yaml", "models\README.md", "scripts\download_data.md") |
    ForEach-Object { Remove-Bom (Join-Path $root $_) }

# ---------------------------------------------------------------
Write-Host "`n[1/5] .gitignore: keep the 570 MB model out of git ..." -ForegroundColor Yellow
$gi = Join-Path $root ".gitignore"
$giText = Get-Content $gi -Raw
if ($giText -notmatch "safetensors") {
    $add = "`n# Large model weights (host on Hugging Face Hub, download at startup)`n*.safetensors`n*.bin`n*.pt`n*.h5`n/model.safetensors`n/tokenizer.json`n"
    [System.IO.File]::AppendAllText($gi, $add, $utf8NoBom)
    Write-Host "  .gitignore updated" -ForegroundColor Green
} else { Write-Host "  already ignored" -ForegroundColor DarkGray }

# ---------------------------------------------------------------
Write-Host "`n[2/5] Copying artifacts into models/<engine>/$version ..." -ForegroundColor Yellow

# --- RAGTruth ---
$rag = "models\ragtruth\$version"
Copy-Files @("model.safetensors","config.json","tokenizer.json","tokenizer_config.json","training_args.bin") "$rag\model"
Copy-Files @("sentinel_config.json","selection.json") $rag
Copy-Files @("evaluation_results.json","confusion_matrix.png","model_comparison.csv","validation_threshold_curve.csv") "$rag\evaluation"

# --- NAB ---
$nab = "models\nab\$version"
$nabModels = Get-ChildItem (Join-Path $root "NAB_outputs\final") -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*_model.joblib" -or $_.Name -like "*_config.json" } |
    ForEach-Object { "NAB_outputs\final\" + $_.Name }
Copy-Files $nabModels $nab
Copy-Files @("NAB_outputs\final\final_metrics.csv","NAB_outputs\final\final_metrics_with_verdict.csv","NAB_outputs\final\all_designs_metrics.csv","NAB_outputs\final\split_manifest.csv","NAB_outputs\final\REPORT.md") "$nab\evaluation"

# --- SMD ---
$smd = "models\smd\$version"
Copy-Files @("smd_outputs\machine-1-1_models.joblib","smd_outputs\machine-1-2_models.joblib","smd_outputs\machine-1-3_models.joblib") $smd
Copy-Files @("smd_outputs\final_results.csv","smd_outputs\final_report.md","smd_outputs\METHODOLOGY.md","smd_outputs\methodology_checks.csv","smd_outputs\iforest_seed_results.csv","smd_outputs\iforest_stability_summary.csv","smd_outputs\model_overlap.csv","smd_outputs\data_summary.csv") "$smd\evaluation"

# --- Notebooks (copied for tidiness) ---
Copy-Files @("214dbb85_SVM_fixed (1).ipynb","Nab_fixed.ipynb","Rag_truth.ipynb","SVM.ipynb") "notebooks"

# ---------------------------------------------------------------
Write-Host "`n[3/5] Hashing files and writing manifests (570 MB file takes a few seconds) ..." -ForegroundColor Yellow
$today = Get-Date -Format "yyyy-MM-dd"

# RAGTruth metadata
$cfg = Read-Json "$rag\model\config.json"
$ragMeta = [ordered]@{
    engine          = "ragtruth"
    version         = $version
    created         = $today
    purpose         = "Detect potentially hallucinated LLM responses (RAGTruth)"
    model_type      = "fine-tuned transformer classifier (Hugging Face safetensors)"
    hf_config       = [ordered]@{
        model_type    = $cfg.model_type
        architectures = $cfg.architectures
        name_or_path  = $cfg._name_or_path
        id2label      = $cfg.id2label
    }
    sentinel_config = (Read-Json "$rag\sentinel_config.json")
    selection       = (Read-Json "$rag\selection.json")
    evaluation      = (Read-Json "$rag\evaluation\evaluation_results.json")
    hosting_note    = "model.safetensors is ~570 MB: not in git. Host on Hugging Face Hub and download at startup."
    limitations     = @("Predefined samples used in the UI demo", "TODO: add dataset/threshold limitations from evaluation")
    python_version  = "3.12.10"
    mlflow_run_id   = $null
    files           = (Get-Manifest $rag)
}
Save-Text "$rag\metadata.json" (ConvertTo-Json -InputObject $ragMeta -Depth 10)

# NAB metadata
$nabMeta = [ordered]@{
    engine         = "nab"
    version        = $version
    created        = $today
    purpose        = "Detect anomalies in single time-series system metrics (Numenta Anomaly Benchmark)"
    model_type     = "one joblib model + config per NAB series (see *_config.json)"
    series         = @($nabModels | ForEach-Object { ($_ -replace '.*\\','') -replace '_model\.joblib|_config\.json','' } | Sort-Object -Unique)
    metrics        = @(Import-Csv (Join-Path $root "$nab\evaluation\final_metrics.csv") -ErrorAction SilentlyContinue)
    limitations    = @("Models are per-series, trained on a 70/30 split of each series", "Predefined samples used in the UI demo")
    python_version = "3.12.10"
    mlflow_run_id  = $null
    files          = (Get-Manifest $nab)
}
Save-Text "$nab\metadata.json" (ConvertTo-Json -InputObject $nabMeta -Depth 10)

# SMD metadata
$smdMeta = [ordered]@{
    engine         = "smd"
    version        = $version
    created        = $today
    purpose        = "Detect unusual patterns across multivariate server metrics (Server Machine Dataset)"
    model_type     = "one joblib model bundle per machine (machine-1-1, machine-1-2, machine-1-3)"
    features       = "21 of 38 metrics used"
    metrics        = @(Import-Csv (Join-Path $root "$smd\evaluation\final_results.csv") -ErrorAction SilentlyContinue)
    limitations    = @("Uses only 21 of the 38 available metrics", "Only 3 machines covered", "Predefined samples used in the UI demo")
    python_version = "3.12.10"
    mlflow_run_id  = $null
    files          = (Get-Manifest $smd)
}
Save-Text "$smd\metadata.json" (ConvertTo-Json -InputObject $smdMeta -Depth 10)
Write-Host "  metadata.json written for all 3 engines (includes sha256 of every file)" -ForegroundColor Green

# ---------------------------------------------------------------
Write-Host "`n[4/5] Size summary ..." -ForegroundColor Yellow
foreach ($e in @("ragtruth","nab","smd")) {
    $mb = (Get-ChildItem (Join-Path $root "models\$e") -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
    "{0,-10} {1,8:N1} MB" -f $e, $mb | Write-Host
}

Write-Host "`n[5/5] Git safety check ..." -ForegroundColor Yellow
git status --short | Select-Object -First 40
Write-Host "`nDone." -ForegroundColor Cyan
Write-Host "CHECK: 'model.safetensors' and anything under models\ragtruth\...\model\ must NOT appear above." -ForegroundColor Cyan
Write-Host "Then send Claude: main.py, sentinel_config.json, selection.json, requirements.txt, tests\test_api.py, scripts\build_artifacts.py" -ForegroundColor Cyan
