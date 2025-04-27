# KnowIt (UWB 2025 Hackathon - Security Track)

# KnowIt Backend  
*Submission for UW Saves The World Hackathon – April 27, 2025*  

This repository contains the backend service for **KnowIt**, a Chrome extension that assesses article reliability and detects phishing in Gmail. The service exposes two HTTP endpoints—`/evaluate` and `/phishing`—that the frontend calls to power its functionality.

---

## 📋 Table of Contents  
- [Features](#features)  
- [Tech Stack & Dependencies](#tech-stack--dependencies)  
- [Environment Variables](#environment-variables)  
- [API Endpoints](#api-endpoints)  
- [Installation & Setup](#installation--setup)  
- [Running the Service](#running-the-service)  
- [Example Requests](#example-requests)  
- [Future Work](#future-work)  
- [License](#license)  

---

## Features  
- **Article Reliability Evaluation**  
  - Scrapes and parses online articles using `newspaper3k`.  
  - Sends cleaned text to the OpenAI API to compute a reliability score and suggest alternative sources.  
- **Gmail Phishing Detection**  
  - Receives raw email content and uses OpenAI to classify phishing risk (numeric score + explanation).  
- **Caching**  
  - `cache_manager.py` prevents repeated LLM calls for the same input, improving response time and reducing API usage.  

---

## Tech Stack & Dependencies  
- **Python 3.8+**  
- **Flask** – HTTP server framework  
- **Flask-CORS** – Cross-origin support for frontend requests  
- **OpenAI Python SDK** – LLM integration  
- **newspaper3k** – Article scraping & text extraction requirements.txt](file-service://file-WKu11AZhCuLbTnmZspmZoj)  

Install dependencies from `requirements.txt`:  
   ```bash   
      pip install -r requirements.txt
   ```

---

## Environment Variables

Before running, set your OpenAI API key:

export OPENAI_API_KEY="sk-…"

---

## API Endpoints

POST /evaluate
	•	Purpose: Compute a reliability score (0–100%) and suggest alternative article URLs.
	•	Request Body (JSON):

{ "content": "<full article text>" }


	•	Response (JSON):

{
  "score": 72,
  "alternatives": [
    "https://reliable-source-1.example",
    "https://reliable-source-2.example"
  ]
}

POST /phishing
	•	Purpose: Analyze an email’s content for phishing risk.
	•	Request Body (JSON):

{ "content": "<raw email HTML/text>" }

	•	Response (JSON):

{
  "phishingsense": 2,
  "explanation": "The email uses urgent language, unfamiliar sender, and suspicious links."
}

---

## Installation & Setup
	1.	Clone this repo:

   git clone https://github.com/yourorg/KnowIt-Backend.git
   cd KnowIt-Backend

	2.	Install dependencies:

   pip install -r requirements.txt

	3.	Export your OpenAI key:

   export OPENAI_API_KEY="sk-…"

---

## Running the Service

Start the Flask server on port 4999 (must match the frontend):

python main.py

By default, CORS is enabled so the Chrome extension can call these endpoints directly.

---

## Example Requests

# Evaluate an article
curl -X POST http://localhost:4999/evaluate \
     -H "Content-Type: application/json" \
     -d '{"content":"<paste article text>"}'

# Check for phishing
curl -X POST http://localhost:4999/phishing \
     -H "Content-Type: application/json" \
     -d '{"content":"<paste raw email HTML/text>"}'

---

## Future Work
-	Persist cache to disk or Redis for cross-instance sharing.
-	Add rate limiting to protect the OpenAI API key.
-	Improve prompt engineering for more nuanced scoring.
-	Deploy to a cloud service (e.g., AWS Lambda + API Gateway).

---

## License

Released under the MIT License. See LICENSE for details.

---

## Technical Table of Contents
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
   pip install -r requirements.txt
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

