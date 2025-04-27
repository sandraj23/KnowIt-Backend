# main_local.py
# ─────────────────────────────────────────────────
# pip install flask flask-cors newspaper3k ollama

import subprocess
import time
import socket
import sys

def ensure_ollama_daemon(host="127.0.0.1", port=11434, timeout=100):
    """ Start `ollama serve` if the daemon isn’t already running. """
    s = socket.socket()
    try:
        s.connect((host, port))
        s.close()
        return
    except OSError:
        print("🔄 Ollama daemon not detected—starting it now...", file=sys.stderr)
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                s = socket.socket()
                s.connect((host, port))
                s.close()
                print("✅ Ollama daemon is up.", file=sys.stderr)
                return
            except OSError:
                time.sleep(0.5)
        print(f"⚠️  Timeout: Ollama daemon did not start within {timeout}s", file=sys.stderr)
        sys.exit(1)

# Start the Ollama daemon
ensure_ollama_daemon()

from flask import Flask, request, jsonify
from flask_cors import CORS

# ← Point here to your Ollama-backed agent
from llm_agent_local import OllamaService
from llm_agent import OpenAIService
from cache_manager import CacheManager
from newspaper import Article

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Pass an empty API key; it's ignored by the local implementation
llm_client_openai = OpenAIService(
)
llm_client = OllamaService(
    api_key="",
    model="mistral",
)
cache_manager = CacheManager(cache_dir="cache")


# ---————— Phishing endpoint ——————#
# Endpoint to handle phishing detection
@app.route('/phishing', methods=['POST'])
def phishing():
    # Check if the request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    # Parse JSON payload
    payload = request.get_json(silent=True)

    # Validate payload
    if not payload or 'content' not in payload:
        return jsonify({"error": "Missing 'content' in request"}), 400

    # Extract HTML content from payload
    content = payload['content']

    try:
        # Call the LLM to evaluate phishing
        result = llm_client_openai.evaluate_phishing(content)
    except Exception as e:
        print("⚠️  Phishing evaluation failed:", e)
        return jsonify({"error": f"Phishing evaluation failed: {e}"}), 500
    
    # Extract the relevant fields from the LLM output
    phishing_result = {
        "phishingsense": result.get("phishingsense"),
        "explanation": result.get("explanation")
    }

    # Output the phishing evaluation result
    return jsonify(phishing_result), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        payload = request.get_json(force=True)
        if not payload or 'content' not in payload or 'url' not in payload:
            return jsonify({"error": "Missing 'content' and 'url'"}), 400

        html = payload['content']
        url  = payload['url']

        # Check if the content is already cached
        cached_response = cache_manager.load_response(html)
        if cached_response:
            print("🔄 Using cached response.")
            print(cached_response)
            return jsonify(cached_response), 200
        print("🔄 No cache found, processing the request...")

        print("🔗 URL:", url)
        print("📰 HTML Content:", html)

        # 1) Extract article content
        extracted = llm_client.extract_article_content(html)

        # 2) Search & compare
        search_cmp = llm_client.search_and_compare(
            topic=extracted.get("topic", ""),
            intent=extracted.get("intent", ""),
            original_claims=extracted.get("claims", []),
        )

        print("🔍 Search & Compare results:", search_cmp)

        # 3) Fetch metadata safely
        try:
            article = Article(url)
            article.download(); article.parse(); article.nlp()
            metadata = {
                "title": article.title,
                "authors": article.authors,
                "summary": article.summary
            }
        except Exception as e:
            print(f"⚠️ Metadata fetch failed: {e}")
            metadata = {"title": "", "authors": [], "summary": ""}

        result = {
            # "extracted": extracted,
            "search_cmp": search_cmp,
            # "metadata": metadata
        }

        cache_manager.save_response(html, result)
        print(result)
        return jsonify(result), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4999, debug=True)