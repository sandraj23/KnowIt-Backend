# reliably

A lightweight Flask-based backend service that evaluates the reliability of web‐scraped articles by extracting key elements (topic, claims, data, intent) via OpenAI and scoring their trustworthiness.

---

## Table of Contents
1. [Features](#features)
2. [Directory Structure](#directory-structure)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Server](#running-the-server)
7. [API Endpoints](#api-endpoints)
   - [GET /health](#get-health)
   - [POST /evaluate](#post-evaluate)
8. [Example Usage (cURL)](#example-usage)
9. [Code Overview](#code-overview)
10. [Troubleshooting](#troubleshooting)

---

## Features
- **HTML‐to‐JSON Extraction**: Uses OpenAI to parse web‑scraped article HTML into four structured fields:
  - `topic` (string)
  - `claims` (list of strings)
  - `data` (list of strings)
  - `intent` (string)
- **Reliability Scoring**: Rates each article on a 1–5 reliability scale with an explanation.
- **CORS‐Enabled**: Ready for integration with a Chrome extension or other frontends.

---

## Directory Structure
```
project-root/
├── main.py           # Flask application and endpoint definitions
├── llm_agent.py      # OpenAIService class encapsulating LLM calls
└── README.md         # This documentation
```

---

## Prerequisites
- Python 3.8+ (tested on 3.12)
- pip
- An OpenAI API key

---

## Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/your-org/reliably.git
   cd reliably
   ```
2. Install dependencies:
   ```bash
   pip install Flask flask-cors openai
   ```

---

## Configuration
Set your OpenAI key in environment or directly in code (not recommended for production):
```bash
export OPENAI_API_KEY="sk-...your-key..."
```

In `main.py`, modify the instantiation if you prefer environment variables:
```python
from llm_agent import OpenAIService
import os

llm_client = OpenAIService(
    api_key=os.getenv('OPENAI_API_KEY')
)
```

---

## Running the Server
```bash
python main.py
# or use flask CLI:
# export FLASK_APP=main.py
# flask run --host=0.0.0.0 --port=4999
```
By default, the service listens on port **4999**.

---

## API Endpoints

### GET /health
Simple health check.
- **Request:** `GET http://<host>:4999/health`
- **Response:** `200 OK` with JSON `{ "status": "healthy" }`

### POST /evaluate
Analyze article HTML and score reliability.

- **Endpoint:** `POST http://<host>:4999/evaluate`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "html_content": "<h1>Title</h1><p>Article body...</p>"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "topic": "...",
    "claims": ["..."],
    "data": ["..."],
    "intent": "...",
    "reliability": {
      "score": 1—5,
      "explanation": "..."
    }
  }
  ```
- **Error Codes:**
  - `400` for malformed JSON or missing `html_content`
  - `500` for LLM extraction/parsing errors

---

## Example Usage (cURL)
```bash
curl -i \
  -X POST http://localhost:4999/evaluate \
  -H "Content-Type: application/json" \
  -d '{"html_content":"<h1>News</h1><p>Scientists confirmed discovery...</p>"}'
```
Use `-i` to see headers and status codes. Pipe to [`jq`](https://stedolan.github.io/jq/) for pretty JSON.

---

## Code Overview

### `main.py`
- Sets up Flask, CORS, and two routes:
  - `/health` (GET): basic status
  - `/evaluate` (POST): calls `OpenAIService` to extract & score

### `llm_agent.py`
- **`OpenAIService`**: encapsulates all OpenAI ChatCompletion calls:
  - `extract_article_content(html_content)` → dict with four fields
  - `score_reliability(info)` → dict with `{score, explanation}`

This separation keeps your Flask routes clean and makes LLM logic reusable.

---

## Troubleshooting
- **`500` errors** typically means the LLM output didn’t parse. Check the raw log in your console for JSON decode errors.
- **CORS issues** in the browser: restrict origins in `CORS(app, …)` to your extension’s ID or domain.

---

*Happy coding!* Feel free to open issues or contribute improvements.

