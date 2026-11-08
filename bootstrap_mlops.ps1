# SentinelAI - MLOps Step 1 bootstrap
# Run from the project root:  C:\Users\Lenovo\Desktop\SentinalAI
#   powershell -ExecutionPolicy Bypass -File .\bootstrap_mlops.ps1
# Safe by design: creates folders/files only if missing. Never moves or deletes anything.

$ErrorActionPreference = "Continue"
$root = Get-Location
Write-Host "Project root: $root" -ForegroundColor Cyan

function Write-IfMissing($path, $content) {
    if (Test-Path $path) { Write-Host "  skip (exists): $path" -ForegroundColor DarkGray; return }
    $dir = Split-Path $path -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Set-Content -Path $path -Value $content -Encoding utf8
    Write-Host "  created: $path" -ForegroundColor Green
}

# ---------------------------------------------------------------
# 1. INVENTORY (paste inventory.txt back to Claude)
# ---------------------------------------------------------------
Write-Host "`n[1/4] Building inventory.txt ..." -ForegroundColor Yellow
$skip = 'NAB-master|OmniAnomaly-master|RAGTruth-main|\\\.git\\|__pycache__|\.pytest_cache|\\\.venv\\|\\venv\\|mlruns'
$out = @()
$out += "=== TOP-LEVEL FILES ==="
$out += Get-ChildItem -File | ForEach-Object { "{0,10:N2} MB  {1}" -f ($_.Length/1MB), $_.Name }
$out += "`n=== FILES IN PROJECT (excluding cloned repos), with sizes ==="
$out += Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch $skip } |
    ForEach-Object { "{0,10:N2} MB  {1}" -f ($_.Length/1MB), $_.FullName.Substring($root.Path.Length+1) }
$out += "`n=== RAGTruth-main\sentinel_work ==="
if (Test-Path "RAGTruth-main\sentinel_work") {
    $out += Get-ChildItem "RAGTruth-main\sentinel_work" -Recurse -File |
        ForEach-Object { "{0,10:N2} MB  {1}" -f ($_.Length/1MB), $_.FullName.Substring($root.Path.Length+1) }
}
$out += "`n=== PYTHON / GIT ==="
$out += (python --version 2>$null)
$out += (git --version 2>$null)
$out += (python -m pip freeze 2>$null)
$out | Set-Content inventory.txt -Encoding utf8
Write-Host "  wrote inventory.txt" -ForegroundColor Green

# ---------------------------------------------------------------
# 2. FOLDER STRUCTURE
# ---------------------------------------------------------------
Write-Host "`n[2/4] Creating folder structure ..." -ForegroundColor Yellow
$dirs = @(
  "src\sentinelai\engines\ragtruth", "src\sentinelai\engines\nab", "src\sentinelai\engines\smd",
  "models\ragtruth\v0.1.0", "models\nab\v0.1.0", "models\smd\v0.1.0",
  "configs", "data", "reports", "docs",
  "tests\unit", "tests\integration",
  ".github\workflows", "scripts"
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null; Write-Host "  created: $d" -ForegroundColor Green }
}

# ---------------------------------------------------------------
# 3. CONFIG FILES
# ---------------------------------------------------------------
Write-Host "`n[3/4] Writing config files ..." -ForegroundColor Yellow

Write-IfMissing ".gitignore" @'
# Python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# Secrets / local config
.env

# MLflow local tracking (keep out of git; export final models to models/)
mlruns/
mlartifacts/

# Raw datasets and cloned upstream repos (reproduce via scripts/download_data.md)
data/
NAB-master/
OmniAnomaly-master/
RAGTruth-main/
NAB_outputs/
smd_outputs/

# Misc
*.log
*.zip
inventory.txt
.DS_Store
'@

Write-IfMissing "pyproject.toml" @'
[project]
name = "sentinelai"
version = "0.1.0"
description = "Unified ML monitoring: hallucination detection (RAGTruth), time-series anomalies (NAB), server anomalies (SMD)"
requires-python = ">=3.10"
dependencies = [
    "fastapi[standard]",
    "pydantic>=2",
    "numpy",
    "pandas",
    "scikit-learn",
    "joblib",
    "pyyaml",
    # TODO: add the exact ML libs your models need (torch / tensorflow / transformers ...)
    # and pin versions from inventory.txt (pip freeze) so builds are reproducible.
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-cov",
    "httpx",
    "ruff",
    "mlflow",
]

[tool.fastapi]
# TODO: point to your real FastAPI app, e.g. "main:app" or "src.sentinelai.api:app"
entrypoint = "main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
extend-exclude = ["NAB-master", "OmniAnomaly-master", "RAGTruth-main"]
'@

Write-IfMissing ".env.example" @'
# Copy to .env (never commit .env)
SENTINELAI_ENV=local
SENTINELAI_LOG_LEVEL=INFO
SENTINELAI_MODELS_DIR=models
# Only needed if models are hosted externally and downloaded at startup:
# SENTINELAI_MODEL_BASE_URL=
MLFLOW_TRACKING_URI=./mlruns
'@

Write-IfMissing "configs\models.yaml" @'
# Single source of truth for which model version each engine serves.
# The API reads this at startup. To roll back, change the version here.
engines:
  ragtruth:
    active_version: v0.1.0
    path: models/ragtruth/v0.1.0
  nab:
    active_version: v0.1.0
    path: models/nab/v0.1.0
  smd:
    active_version: v0.1.0
    path: models/smd/v0.1.0
'@

$meta = @'
{
  "engine": "ENGINE_NAME",
  "version": "v0.1.0",
  "created": "YYYY-MM-DD",
  "model_type": "TODO (e.g. IsolationForest / LSTM / classifier)",
  "artifact_files": ["TODO model file names"],
  "training_data": "TODO dataset + split",
  "features": "TODO (SMD: 21 of 38 metrics - list them)",
  "metrics": { "precision": null, "recall": null, "f1": null },
  "threshold": null,
  "mlflow_run_id": null,
  "limitations": ["TODO"],
  "python_version": "TODO",
  "library_versions": {}
}
'@
foreach ($e in @("ragtruth","nab","smd")) {
    Write-IfMissing "models\$e\v0.1.0\metadata.json" ($meta -replace "ENGINE_NAME", $e)
}

Write-IfMissing "models\README.md" @'
# Model artifacts

Layout: `models/<engine>/<version>/` containing the model file(s) and `metadata.json`.

Rules
- Never overwrite a released version. New model = new version folder.
- Every version has a filled-in `metadata.json` (data, metrics, threshold, features, limitations).
- `configs/models.yaml` selects the active version per engine.
- Large binaries: if a model is much bigger than ~10 MB, host it externally and download at startup.
'@

Write-IfMissing "scripts\download_data.md" @'
# Re-creating the raw data (not stored in git)

- NAB: clone https://github.com/numenta/NAB into `NAB-master/`
- SMD / OmniAnomaly: clone https://github.com/NetManAIOps/OmniAnomaly into `OmniAnomaly-master/`
- RAGTruth: clone https://github.com/ParticleMedia/RAGTruth into `RAGTruth-main/`

TODO: replace with a script that fetches the exact versions used.
'@

# ---------------------------------------------------------------
# 4. GIT
# ---------------------------------------------------------------
Write-Host "`n[4/4] Git ..." -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    git init | Out-Null
    Write-Host "  git initialised" -ForegroundColor Green
} else {
    Write-Host "  git repo already exists" -ForegroundColor DarkGray
}

Write-Host "`nDone. Next: open inventory.txt, paste it to Claude." -ForegroundColor Cyan
Write-Host "Before first commit run:  git status   (make sure NAB-master etc. are NOT listed)" -ForegroundColor Cyan

