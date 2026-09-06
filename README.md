# 🌐 Indian Language Translation API

A fast, lightweight, and production-ready Translation REST API supporting **English, Hindi, Punjabi, Gujarati, and Marathi**.

* **Live Base URL:** `https://translator-api-4sky.onrender.com`
* **Interactive Swagger UI:** `https://translator-api-4sky.onrender.com/docs`
* **Alternative ReDoc UI:** `https://translator-api-4sky.onrender.com/redoc`

---

## 🚀 Supported Languages

Use the following exact lowercase language strings in your API requests:

| Language | API String | Script | Example Input |
|---|---|---|---|
| **English** | `"english"` | Latin | `"Hello, how are you?"` |
| **Hindi** | `"hindi"` | Devanagari | `"नमस्ते, आप कैसे हैं?"` |
| **Punjabi** | `"punjabi"` | Gurmukhi | `"ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?"` |
| **Gujarati** | `"gujarati"` | Gujarati | `"નમસ્તે, તમે કેમ છો?"` |
| **Marathi** | `"marathi"` | Devanagari | `"नमस्कार, तुम्ही कसे आहात?"` |

> **Direct Translation Matrix:** Every pair works directly (English ↔ Indic and Indic ↔ Indic).

---

## 📡 API Endpoints Reference

### 1. Translate Text
Translates text between any two supported languages.

* **URL:** `/translate`
* **Method:** `POST`
* **Headers:**
  * `Content-Type: application/json`

#### Request Body Schema
| Field | Type | Required | Description |
|---|---|---|---|
| `text` | `string` | **Yes** | The text to translate. |
| `source_language` | `string` | **Yes** | Source language (`"english"`, `"hindi"`, `"punjabi"`, `"gujarati"`, `"marathi"`). |
| `target_language` | `string` | **Yes** | Target language (`"english"`, `"hindi"`, `"punjabi"`, `"gujarati"`, `"marathi"`). |

#### Example Request
```json
{
  "text": "Hello, how are you? Welcome to our platform.",
  "source_language": "english",
  "target_language": "punjabi"
}
```

#### Example Response (`200 OK`)
```json
{
  "original_text": "Hello, how are you? Welcome to our platform.",
  "translated_text": "ਹੈਲੋ ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ? ਸਾਡੇ ਪਲੇਟਫਾਰਮ 'ਤੇ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ।",
  "source_language": "english",
  "target_language": "punjabi"
}
```

---

### 2. List Supported Languages
Returns the full list of supported language names.

* **URL:** `/languages`
* **Method:** `GET`

#### Example Response (`200 OK`)
```json
{
  "supported_languages": [
    "english",
    "hindi",
    "punjabi",
    "gujarati",
    "marathi"
  ]
}
```

---

### 3. Health Check
Checks if the server is healthy and reports backend configuration.

* **URL:** `/health`
* **Method:** `GET`

#### Example Response (`200 OK`)
```json
{
  "status": "ok",
  "model": "facebook/nllb-200-distilled-600M",
  "backend": "HF Inference API",
  "hf_token_set": true
}
```

---

## ⚠️ HTTP Status Codes & Error Handling

| Status Code | Meaning | Cause |
|---|---|---|
| **`200 OK`** | Success | Text was translated successfully. |
| **`400 Bad Request`** | Invalid input | Unsupported language specified. |
| **`422 Unprocessable`**| Validation error | Missing required fields (`text`, `source_language`, or `target_language`). |
| **`502 Bad Gateway`** | Upstream Error | Translation provider was temporarily unreachable. |
| **`503 Service Unavailable`** | Loading | Model is spinning up; retry in a few seconds. |

#### Error Response Format
```json
{
  "detail": "Unsupported source language 'french'. Supported: ['english', 'hindi', 'punjabi', 'gujarati', 'marathi']"
}
```

---

## 💻 Backend Integration Code Examples

### 1. Node.js (Fetch API / Express / Next.js)
```javascript
async function translate(text, sourceLang, targetLang) {
  const response = await fetch("https://translator-api-4sky.onrender.com/translate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text: text,
      source_language: sourceLang,
      target_language: targetLang,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(`Translation error: ${errorData.detail || response.statusText}`);
  }

  const data = await response.json();
  return data.translated_text;
}

// Example usage:
translate("Welcome to our service", "english", "hindi")
  .then((res) => console.log("Translated:", res))
  .catch((err) => console.error(err));
```

---

### 2. Node.js (Axios)
```javascript
const axios = require('axios');

async function translate(text, sourceLang, targetLang) {
  const { data } = await axios.post('https://translator-api-4sky.onrender.com/translate', {
    text: text,
    source_language: sourceLang,
    target_language: targetLang,
  });
  return data.translated_text;
}
```

---

### 3. Python (`requests` / FastAPI / Django / Flask)
```python
import requests

def translate(text: str, source_language: str, target_language: str) -> str:
    url = "https://translator-api-4sky.onrender.com/translate"
    payload = {
        "text": text,
        "source_language": source_language,
        "target_language": target_language,
    }
    
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    return data["translated_text"]

# Example:
punjabi_text = translate("Good morning, have a great day!", "english", "punjabi")
print("Result:", punjabi_text)
```

---

### 4. cURL (Command Line)
```bash
curl -X POST "https://translator-api-4sky.onrender.com/translate" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Hello world",
       "source_language": "english",
       "target_language": "hindi"
     }'
```

---

## ⚙️ Technical Requirements & Architecture

* **Framework:** FastAPI (Python 3.11)
* **Runtime:** Docker on Linux (Debian slim)
* **RAM Requirement:** ~80 MB (runs effortlessly on free hosting tiers)
* **Cold Starts:** On Render Free Tier, services idle after 15 minutes of inactivity. The first request takes ~10–15s to wake up; all subsequent requests respond in <1 second.
* **CORS:** Enabled for all origins (`*`) — frontend applications can call this API directly.
