#Install Flask and OpenAI : pip install Flask openai flask-cors

from flask import Flask, request, jsonify
from flask_cors import CORS
from llm_agent import OpenAIService


# —————— Flask & CORS setup ——————#
# Initialize Flask app and enable CORS for all routes
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# —————— LLM client init ——————#
# Initialize the OpenAI client with the provided API key and model
llm_client = OpenAIService(
    api_key="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"
)

# —————— Health‐check endpoint ——————#
# Simple health-check endpoint to verify the service is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200


# —————— Evaluate endpoint ——————#
# Endpoint to handle incoming data
@app.route('/evaluate', methods=['POST'])
def evaluate():

    # Check if the request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    # Parse JSON payload
    payload = request.get_json(silent=True)

    # Validate payload
    if not payload or 'html_content' not in payload:
        return jsonify({"error": "Missing 'html_content' in request"}), 400

    # Extract HTML content from payload
    html_content = payload['html_content']

    try:
        extracted = llm_client.extract_article_content(html_content)
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {e}"}), 500
    
    # Extract the relevant fields from the LLM output
    article_context = {
        "topic": extracted.get("topic"),
        "claims": extracted.get("claims"),
        "data": extracted.get("data"),
        "intent": extracted.get("intent")
    }

    # Output the extracted article context
    return jsonify(article_context), 200



# —————— Main entry point ——————#
# Run the Flask app
# This will start the server and listen for incoming requests
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4999, debug=True)