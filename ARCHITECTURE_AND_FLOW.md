# 📘 Indian Language Translation API — System Architecture, Workflow & Technical Guide

---

## 📑 Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Supported Languages & Code Mappings](#2-supported-languages--code-mappings)
3. [System Architecture & Multi-Tier Resilience](#3-system-architecture--multi-tier-resilience)
4. [External Sources & Cloud Services](#4-external-sources--cloud-services)
5. [Internal Tools & Library Stack](#5-internal-tools--library-stack)
6. [End-to-End Request Execution Flow](#6-end-to-end-request-execution-flow)
7. [API Endpoints Reference](#7-api-endpoints-reference)
8. [Benchmarking, Performance & Quality Assurance](#8-benchmarking-performance--quality-assurance)
9. [Local Development, Testing & Deployment](#9-local-development-testing--deployment)

---

## 1. Executive Summary

The **Indian Language Translation API** is a production-grade, containerized REST API built with Python and FastAPI. It specializes in high-fidelity translations across **5 languages**:
* **English**
* **Hindi**
* **Punjabi**
* **Gujarati**
* **Marathi**

### Key Characteristics:
* **All 20 Pairs Direct**: Translates English ↔ Indic and Indic ↔ Indic without requiring manual pivots where direct models are available.
* **Ultra-Low Memory Footprint (~80 MB RAM)**: Instead of bundling gigabytes of deep learning weights directly on the host (which causes out-of-memory crashes on free-tier cloud instances), the service delegates inference to high-availability upstream APIs.
* **Multi-Tier Cascade**: Implements an automatic 3-layer fallback mechanism (MyMemory $\rightarrow$ Hugging Face NLLB-200 $\rightarrow$ LLM Chat Router) to ensure continuous uptime and zero dead-ends.
* **Production Ready**: Full Docker containerization with non-root user permissions, dynamic port binding, CORS enabled for all origins, and automated OpenAPI documentation.

---

## 2. Supported Languages & Code Mappings

The system utilizes standard two-letter ISO language codes for MyMemory and BCP-47 / FLORES-200 language-script tags for Hugging Face NLLB models:

| Language Name | API Key (`source_language` / `target_language`) | MyMemory / ISO Code | NLLB-200 FLORES Code | Native Script |
|---|---|---|---|---|
| **English** | `"english"` | `en` | `eng_Latn` | Latin |
| **Hindi** | `"hindi"` | `hi` | `hin_Deva` | Devanagari |
| **Punjabi** | `"punjabi"` | `pa` | `pan_Guru` | Gurmukhi |
| **Gujarati** | `"gujarati"` | `gu` | `guj_Gujr` | Gujarati |
| **Marathi** | `"marathi"` | `mr` | `mar_Deva` | Devanagari |

---

## 3. System Architecture & Multi-Tier Resilience

The service is engineered with a **fail-safe cascading design pattern**:

```
                  ┌──────────────────────────────┐
                  │        Incoming Request      │
                  │       (POST /translate)      │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │    FastAPI + Pydantic        │
                  │    - Validate schema         │
                  │    - Check language codes    │
                  │    - Identity check (src==tgt│
                  └──────────────┬───────────────┘
                                 │
                 ┌───────────────┴──────────────┐
                 │                              │
          (Valid pair)                     (Invalid)
                 │                              │
                 ▼                              ▼
    ┌───────────────────────────┐     ┌───────────────────┐
    │  Tier 1: MyMemory REST    │     │ HTTP 400 / 422    │
    │  - Direct query           │     └───────────────────┘
    │  - Confidence filter >=0.5│
    │  - Indic-to-Indic pivot   │
    └────────────┬──────────────┘
                 │
           ┌─────┴──────────────┐
       [Success]             [Failure]
           │                    │
           ▼                    ▼
    ┌──────────────┐   ┌───────────────────────────┐
    │ 200 OK Return│   │  Tier 2: HF NLLB-200      │
    └──────────────┘   │  - Task endpoint inference│
                       └────────────┬──────────────┘
                                    │
                              ┌─────┴──────────────┐
                          [Success]             [Failure]
                              │                    │
                              ▼                    ▼
                       ┌──────────────┐   ┌───────────────────────────┐
                       │ 200 OK Return│   │  Tier 3: HF Chat Fallback │
                       └──────────────┘   │  - Llama 3.1 8B Instruct  │
                                          │  - Qwen 2.5 7B Instruct   │
                                          │  - Mistral 7B Instruct    │
                                          └────────────┬──────────────┘
                                                       │
                                                 ┌─────┴──────────────┐
                                             [Success]             [Failure]
                                                 │                    │
                                                 ▼                    ▼
                                          ┌──────────────┐   ┌───────────────────┐
                                          │ 200 OK Return│   │ HTTP 502 / 503    │
                                          └──────────────┘   └───────────────────┘
```

---

## 4. External Sources & Cloud Services

### 1. MyMemory Translation API (`api.mymemory.translated.net`)
* **Role**: Primary translation provider.
* **Mechanism**: REST GET requests over HTTPS (`https://api.mymemory.translated.net/get?q={text}&langpair={src}|{tgt}`).
* **Quality Guard**: MyMemory provides a `match` score (0.0 to 1.0). Our backend enforces a **confidence threshold** (`match_score >= 0.5`). Crowdsourced low-quality translations or spam are automatically discarded.
* **Indic-to-Indic Pivot**: For obscure Indic pairs where MyMemory's direct database is sparse, the engine automatically pivots through English: $Source \rightarrow English \rightarrow Target$.

### 2. Hugging Face Inference API (`router.huggingface.co`)
* **Role**: Secondary translation engine and deep fallback.
* **NLLB-200 Model**: `facebook/nllb-200-distilled-600M`
  * Trained by Meta AI on 200+ languages natively.
  * Direct translation across all Indic scripts without lexical drift.
* **LLM Chat Fallback**:
  * Models: `meta-llama/Llama-3.1-8B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3`.
  * Invoked if the task-specific NLLB endpoint is busy, warming up (HTTP 503), or unavailable.
  * Uses a strict system prompt instructing the LLM to output pure translated text with zero conversational fluff.

### 3. Render Cloud Platform (`onrender.com`)
* **Role**: Production web hosting environment.
* **Live Service**: `https://translator-api-4sky.onrender.com`
* **Features**: Automated GitHub deployment, SSL/TLS termination, health checks, and Docker container execution.

---

## 5. Internal Tools & Library Stack

| Component / Tool | Technology | File / Path | Purpose |
|---|---|---|---|
| **API Framework** | `FastAPI 0.104+` | `app.py` | Asynchronous routing, middleware, and auto-generated Swagger UI. |
| **ASGI Server** | `Uvicorn 0.24+` | `Dockerfile`, `app.py` | Production HTTP server executing ASGI applications. |
| **Data Validation** | `Pydantic` | `app.py` | Strict typing and schema enforcement for incoming and outgoing payloads. |
| **CORS Middleware** | `CORSMiddleware` | `app.py` | Permits Cross-Origin Resource Sharing from any external client/domain (`*`). |
| **HTTP Client** | `Requests 2.28+` | `app.py`, `benchmark_suite.py` | Executes synchronous outbound HTTP calls with configurable timeouts. |
| **Containerization** | `Docker` | `Dockerfile` | Python 3.10 slim container running as non-root user (`user:1000`). |
| **Benchmark Suite** | `Python standard lib` | `benchmark_suite.py` | ThreadPoolExecutor load tests, latency profiling, and edge-case evaluation. |
| **Mock Test Suite** | `unittest.mock` | `test_mock.py` | Tests network failures, fallbacks, and status codes in offline mode. |

---

## 6. End-to-End Request Execution Flow

When a client calls `POST /translate`:

1. **Schema Parsing**:
   * Pydantic parses JSON body: `{"text": "...", "source_language": "...", "target_language": "..."}`.
   * If any field is missing or invalid type, returns `422 Unprocessable Entity`.
2. **Language Validation**:
   * Cleans strings: `.strip().lower()`.
   * Verifies both keys exist in `LANG_CODES`. If invalid, returns `400 Bad Request`.
3. **Identity Bypass**:
   * If `source_language == target_language`, immediately returns the input string (0 ms overhead).
4. **Tier 1 (MyMemory Direct)**:
   * Queries MyMemory API.
   * Rejects responses containing error phrases or `match_score < 0.5`.
   * Returns immediately if valid.
5. **Tier 1.5 (MyMemory English Pivot)**:
   * If source and target are both Indic languages, translates Source $\rightarrow$ English, then English $\rightarrow$ Target.
   * Returns if both steps produce high-confidence text.
6. **Tier 2 (Hugging Face NLLB-200)**:
   * Passes FLORES language codes (e.g. `hin_Deva` $\rightarrow$ `pan_Guru`) to the Hugging Face router.
   * If the model returns `translation_text`, returns 200 OK.
   * If HF returns 503 (model spinning up), propagates a helpful waiting estimate.
7. **Tier 3 (Hugging Face LLM Fallback)**:
   * Iterates through candidate chat models (`Llama-3.1-8B`, `Qwen2.5-7B`, `Mistral-7B`).
   * Feeds the text with zero-temperature translation instructions.
   * Strips any extraneous whitespace and returns the first valid response.
8. **Final Error Bubble-Up**:
   * If all tiers fail, raises `HTTP 502 Bad Gateway` with diagnostic error details.

---

## 7. API Endpoints Reference

### 1. `POST /translate`
Translates text between any two supported languages.

* **Request Headers**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "text": "Hello, how are you? Welcome to our platform.",
  "source_language": "english",
  "target_language": "punjabi"
}
```
* **Response Body (`200 OK`)**:
```json
{
  "original_text": "Hello, how are you? Welcome to our platform.",
  "translated_text": "ਹੈਲੋ ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ? ਸਾਡੇ ਪਲੇਟਫਾਰਮ 'ਤੇ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ।",
  "source_language": "english",
  "target_language": "punjabi"
}
```

### 2. `GET /languages`
Lists all supported language keys.
* **Response (`200 OK`)**:
```json
{
  "supported_languages": ["english", "hindi", "punjabi", "gujarati", "marathi"]
}
```

### 3. `GET /health`
Returns system status and model backend information.
* **Response (`200 OK`)**:
```json
{
  "status": "ok",
  "model": "facebook/nllb-200-distilled-600M",
  "backend": "HF Inference API",
  "hf_token_set": true
}
```

### 4. `GET /debug-hf`
Diagnostic endpoint verifying outbound connectivity to Hugging Face router endpoints.

---

## 8. Benchmarking, Performance & Quality Assurance

The live API has been verified using `benchmark_suite.py` against all 20 language pairs and edge cases:

### Performance Metrics (`benchmark_results.json`):
* **Total Pairs Tested**: 20/20
* **Success Rate**: **100.0%**
* **Mean Latency**: **1572.27 ms**
* **Median Latency**: **1672.20 ms**
* **Fastest Response**: **763.24 ms**
* **P95 Latency**: **1866.80 ms**
* **Memory Usage**: **~80 MB RAM** on Linux container

### Edge Cases Tested & Verified:
* **Identity check (`EN -> EN`, `HI -> HI`)**: Passes in <1ms without hitting external networks.
* **Punctuation & Numerics**: Preserves numbers and symbols (e.g. `2026, 100% of 500+`).
* **Whitespace Handling**: Strips unnecessary whitespace safely.
* **Invalid Language Codes**: Returns clean `400 Bad Request` with an explicit list of supported languages.

---

## 9. Local Development, Testing & Deployment

### 1. Local Setup
```powershell
# Clone or open directory
cd "d:\Translation api\translation-api"

# Install dependencies
pip install -r requirements.txt

# Start the local development server with auto-reload
uvicorn app:app --reload --port 8000
```
Open `http://localhost:8000/docs` in your browser to test endpoints interactively via Swagger UI.

### 2. Running Verification Suites
```powershell
# Run offline mock tests (no internet required)
python test_mock.py

# Run the live benchmark suite across all 20 pairs
python benchmark_suite.py
```

### 3. Docker Deployment
```bash
# Build Docker image
docker build -t translation-api .

# Run Docker container locally
docker run -p 8080:8080 -e PORT=8080 translation-api
```
