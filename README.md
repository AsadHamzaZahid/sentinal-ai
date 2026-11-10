# 🛡️ SentinelAI

**An AI-powered hallucination detection and time-series anomaly monitoring platform.**

SentinelAI is a FastAPI-based application designed to help identify potentially hallucinated AI-generated responses and detect unusual patterns in time-series data. It combines a RAGTruth-based hallucination detection pipeline with anomaly detection capabilities using the Server Machine Dataset (SMD) and Numenta Anomaly Benchmark (NAB).

The project provides separate demo and live Docker deployments, API access, interactive API documentation, and automated CI/CD workflows through GitHub Actions.

## 🌐 Live Application

| Resource | Link |
|---|---|
| Live application | https://sentinalai.fastapicloud.dev/ |
| API documentation | https://sentinalai.fastapicloud.dev/docs |
| GitHub repository | https://github.com/AsadHamzaZahid/sentinal-ai |
| Demo Docker image | https://github.com/AsadHamzaZahid/sentinal-ai/pkgs/container/sentinelai-demo |
| Live Docker image | https://github.com/AsadHamzaZahid/sentinal-ai/pkgs/container/sentinelai-live |

## ✨ Key Features

- **AI Hallucination Detection:** Evaluates generated responses against their source information using a ModernBERT-based RAGTruth model in live mode.
- **Multiple Task Types:** Supports Data2txt, QA, and Summary tasks.
- **Sensitivity Modes:** Provides three detection thresholds to adjust how aggressively responses are flagged.
- **Precomputed Demo:** Supports demonstration using stored RAGTruth samples without requiring live model inference.
- **Time-Series Anomaly Detection:** Includes SMD and NAB-based anomaly monitoring components.
- **REST API:** Built using FastAPI, with interactive Swagger documentation.
- **Docker Deployments:** Provides separate demo and live Docker configurations.
- **Automated CI/CD:** Uses GitHub Actions to run tests and build and publish Docker images to GitHub Container Registry.

## 🧠 System Architecture

SentinelAI has two main monitoring components.

### 1. RAGTruth Hallucination Detection

The RAGTruth component evaluates whether an AI-generated response may contain information unsupported by its source.

It supports three operating modes:

| Mode | Description |
|---|---|
| Live | Uses the trained ModernBERT model for inference when the model files are available. |
| Precomputed | Uses stored demonstration samples and their existing predictions. |
| Mock | Uses a lightweight heuristic scoring method for testing and CI. |

The default `auto` configuration selects live inference when the required model files are available. Otherwise, it falls back to precomputed samples when available.

Supported task types:

- Data2txt
- QA
- Summary

Available sensitivity presets:

| Sensitivity mode | Threshold |
|---|---:|
| Catch as many as possible | 0.25 |
| Balanced detection | 0.31 |
| Only flag stronger signals | 0.51 |

A response is flagged when its prediction probability meets or exceeds the selected threshold.

### 2. Time-Series Anomaly Detection

SentinelAI also includes time-series anomaly detection components.

**Server Machine Dataset (SMD)**

- Includes machine-specific anomaly detection models.
- Three machine models were verified loading successfully.
- Supports machine-level demonstration through the API.
- Uses saved thresholds for anomaly decisions.

**Numenta Anomaly Benchmark (NAB)**

- Includes nine prepared time-series configurations.
- Provides anomaly scoring and detection functionality.
- A synthetic spike test successfully triggered anomaly detection.

These demonstrations verify functionality, not overall benchmark accuracy.

## 🏗️ Technology Stack

- Python 3.12
- FastAPI
- Uvicorn
- PyTorch
- Hugging Face Transformers
- ModernBERT
- NumPy
- Scikit-learn
- Docker
- Docker Compose
- GitHub Actions
- GitHub Container Registry

## 🐳 Docker Deployments

SentinelAI provides two independent Docker deployments.

### Demo Deployment

The demo deployment uses precomputed demonstration data.

| Property | Value |
|---|---|
| Dockerfile | `Dockerfile` |
| Requirements | `requirements.docker.txt` |
| Compose file | `compose.yaml` |
| Container | `sentinelai-api` |
| Image | `ghcr.io/asadhamzazahid/sentinelai-demo:latest` |
| Local URL | http://localhost:8000 |

Start the demo:

```bash
docker compose up -d
```

### Live Deployment

The live deployment supports model-based inference and uses externally mounted model files.

| Property | Value |
|---|---|
| Dockerfile | `Dockerfile.live` |
| Requirements | `requirements.live.txt` |
| Compose file | `compose.live.yaml` |
| Container | `sentinelai-live` |
| Image | `ghcr.io/asadhamzazahid/sentinelai-live:latest` |
| Local URL | http://localhost:8001 |

Start the live deployment:

```bash
docker compose -f compose.live.yaml up -d
```

The live deployment requires the relevant model weights and supporting files to be available at the expected host paths. The model weights are mounted into the container rather than packaged inside the live Docker image.

### Useful Docker Commands

Check running containers:

```bash
docker ps
```

View demo logs:

```bash
docker logs sentinelai-api
```

View live logs:

```bash
docker logs sentinelai-live
```

Stop the demo:

```bash
docker compose down
```

Stop the live deployment:

```bash
docker compose -f compose.live.yaml down
```

## 🔌 API Usage

The application provides a REST API through FastAPI.

Interactive documentation:

```text
http://localhost:8001/docs
```

Public documentation:

https://sentinalai.fastapicloud.dev/docs

### Health Check

```http
GET /health
```

Checks the application and reports available model and monitoring components.

### Operating Modes

```http
GET /modes
```

Returns the available task types, sensitivity presets, and active RAGTruth engine mode.

### RAGTruth Prediction

```http
POST /predict
```

Example request:

```json
{
  "task_type": "QA",
  "source_info": "The Eiffel Tower was completed in 1889.",
  "response": "The Eiffel Tower was completed in 1889.",
  "sensitivity_mode": "Balanced detection"
}
```

### Batch Prediction

```http
POST /predict/batch
```

Accepts a list of prediction requests.

### Demonstration Samples

```http
GET /ragtruth/samples
```

Returns available precomputed RAGTruth demonstration samples.

### SMD Demonstration

```http
GET /smd/demo?machine=machine-1-1&length=100
```

Provides a machine-level demonstration using the configured SMD model.

For the complete and current request schemas, consult the Swagger documentation.

## ⚙️ Running Locally

### Requirements

- Python 3.12
- Docker and Docker Compose for containerized deployment
- Git
- Required model files for live inference

### Clone the Repository

```bash
git clone https://github.com/AsadHamzaZahid/sentinal-ai.git
cd sentinal-ai
```

### Install Dependencies

For the main development environment:

```bash
python -m pip install -r requirements.txt
```

For the demo Docker deployment, the project uses:

```text
requirements.docker.txt
```

For the live Docker deployment, the project uses:

```text
requirements.live.txt
```

### Start the Application

Use the appropriate Docker Compose configuration described in the Docker Deployments section.

## 🔄 CI/CD Pipeline

SentinelAI uses GitHub Actions for continuous integration and continuous delivery.

### Continuous Integration

The CI workflow:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Installs project dependencies.
4. Installs pytest and HTTPX.
5. Runs the API test suite.

The CI environment explicitly uses mock mode to test API behavior without requiring large live model weights.

**Verified result:** A GitHub Actions CI run completed successfully after the mock-mode handling was corrected.

### Continuous Delivery

The CD workflow:

1. Checks out the repository.
2. Sets up Docker Buildx.
3. Authenticates with GitHub Container Registry.
4. Builds the demo Docker image.
5. Builds the live Docker image.
6. Publishes both images with `latest` and commit-specific tags.

**Verified result:** The GitHub Actions CD workflow completed successfully, and both Docker packages were visible in GitHub Container Registry.

Published images:

```text
ghcr.io/asadhamzazahid/sentinelai-demo:latest
ghcr.io/asadhamzazahid/sentinelai-live:latest
```

```text
ghcr.io/asadhamzazahid/sentinelai-demo:<commit-sha>
ghcr.io/asadhamzazahid/sentinelai-live:<commit-sha>
```

## 📊 Testing and Verification

The following functionality was exercised during project verification:

| Component | Verification |
|---|---|
| FastAPI application | Started successfully |
| Health endpoint | Returned healthy status |
| RAGTruth live model | ModernBERT loaded successfully |
| RAGTruth demo mode | Precomputed sample functionality available |
| RAGTruth task types | Data2txt, QA, and Summary supported |
| SMD | Three machine models loaded |
| SMD thresholds | Nine saved thresholds loaded |
| NAB | Nine prepared time-series configurations available |
| NAB synthetic spike | Injected spike successfully detected |
| Docker demo | Container started successfully |
| Docker live | Container started successfully |
| GitHub Actions CI | Successful run verified |
| GitHub Actions CD | Successful image publishing run verified |

These checks establish that the application components and deployment workflows functioned in the tested scenarios. They should not be interpreted as a comprehensive accuracy evaluation.

## ⚠️ Limitations and Considerations

Transparency about the current implementation is important.

1. **Hallucination detection accuracy:** A comprehensive independent evaluation on a held-out labeled test set has not been established here. Successful inference examples do not prove overall accuracy.
2. **Sensitivity thresholds:** The configured thresholds control flagging behavior. They do not guarantee a particular precision, recall, or false-positive rate.
3. **Mock mode:** Mock mode uses heuristic scoring. It is intended for testing and must not be treated as equivalent to trained-model inference.
4. **Precomputed mode:** Precomputed mode only supports matching stored samples. It does not provide unrestricted live scoring.
5. **Model weights:** The live Docker image does not package the approximately 571 MB of model weights. They must be supplied through the configured host mounts.
6. **Anomaly detection evaluation:** The SMD and NAB functionality was exercised, but the tests described here do not establish comprehensive benchmark performance.
7. **Production deployment:** GHCR image publishing is automated. This alone does not prove that every repository push automatically deploys the application to a production server.
8. **Compute requirements:** Live inference uses CPU when CUDA is unavailable. Performance will depend on available hardware and workload.

## 📁 Important Project Files

| File or directory | Purpose |
|---|---|
| `main.py` | FastAPI application and inference logic |
| `Dockerfile` | Demo Docker image |
| `Dockerfile.live` | Live Docker image |
| `compose.yaml` | Demo deployment configuration |
| `compose.live.yaml` | Live deployment configuration |
| `requirements.txt` | Main Python dependencies |
| `requirements.docker.txt` | Demo container dependencies |
| `requirements.live.txt` | Live container dependencies |
| `.github/workflows/ci.yml` | Automated testing workflow |
| `.github/workflows/cd.yml` | Docker image publishing workflow |
| `data/demo/` | Demonstration data |
| `models/` | Model configurations and supporting assets |
| `artifacts/` | Deployment and threshold artifacts |
| `NAB_outputs/prepared/` | Prepared NAB time-series data |
| `tests/` | API tests |

## 🚀 Future Improvements

Potential next steps include:

- Conducting a comprehensive held-out RAGTruth evaluation.
- Reporting precision, recall, F1-score, and calibration results.
- Evaluating anomaly detection performance across complete benchmark datasets.
- Improving inference performance and resource utilization.
- Adding monitoring, structured logging, and operational metrics.
- Automating deployment of published images to a production server.
- Expanding API integration and automated testing.

## 👨‍💻 Project

**SentinelAI**

Repository: https://github.com/AsadHamzaZahid/sentinal-ai

Live application: https://sentinalai.fastapicloud.dev/

Built with Python, FastAPI, machine learning, Docker, and GitHub Actions.

---

*SentinelAI is a machine learning monitoring project. Its predictions should be treated as decision-support signals rather than definitive proof that a response is correct or incorrect.*
