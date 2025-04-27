#Install Flask and OpenAI : pip install Flask openai flask-cors

from flask import Flask, request, jsonify
from flask_cors import CORS
from llm_agent import OpenAIService
from cache_manager import CacheManager
from newspaper import Article


# —————— Flask & CORS setup ——————#
# Initialize Flask app and enable CORS for all routes
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# —————— LLM client init ——————#
# Initialize the OpenAI client with the provided API key and model
llm_client = OpenAIService(
    api_key="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"
)

# —————— Cache manager init ——————#
# Initialize the cache manager to store LLM responses
cache_manager = CacheManager(cache_dir="cache")

# —————— Health‐check e ndpoint ——————#
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
    if not payload or 'content' not in payload or 'url' not in payload:
        return jsonify({"error": "Missing parameters in request"}), 400

    # Extract HTML content from payload
    content = payload['content']
    url = payload['url']

    try:
        # Try the cache first
        cached_response = cache_manager.load_response(content)
        # if cached_response:
        #     return jsonify(cached_response), 200
        
        # If not cached, call the LLM to extract article content
        # and save the response to the cache

        # Step 1: Extract article info
        extracted = llm_client.extract_article_content(content)
        print("Extracted info:", extracted)

        # Step 2: Live search and compare claims
        search_comparison = llm_client.search_and_compare(
            topic=extracted.get("topic"),
            intent=extracted.get("intent"),
            original_claims=extracted.get("claims")
        )

        # Step 3: Save cache (only extracted info for now, optional to extend)
        cache_manager.save_response(content, extracted)
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {e}"}), 500
    
    # Extract the relevant fields from the LLM output
    article_context = {
        "topic": extracted.get("topic"),
        "claims": extracted.get("claims"),
        "data": extracted.get("data"),
        "intent": extracted.get("intent")
    }




    # Stuff for metadata evaluation
    # Step 4: Use Newspaper3k to extract metadata
    article = Article(url)
    article.download()
    article.parse()
    # Extract metadata
    article_title = article.title
    article_authors = article.authors
    article_content = article.text
    
    # Step 5: Use LLM to evaluate metadata
    metadata_evaluation = llm_client.evaluate_article_metadata(
        article_title,
        article_authors,
        article_content
    )

    # Step 6: Combine all results
    print("Metadata evaluation:", metadata_evaluation)

    # Combine all results into a single response
    combined_result = {
        "article_context": article_context,
        "metadata_evaluation": metadata_evaluation
    }

    # Output the combined result
    return jsonify(combined_result), 200



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
        result = llm_client.evaluate_phishing(content)
    except Exception as e:
        return jsonify({"error": f"Phishing evaluation failed: {e}"}), 500
    
    # Extract the relevant fields from the LLM output
    phishing_result = {
        "phishingsense": result.get("phishingsense"),
        "explanation": result.get("explanation")
    }

    # Output the phishing evaluation result
    return jsonify(phishing_result), 200
    

        



# —————— Main entry point ——————#
# Run the Flask app
# This will start the server and listen for incoming requests
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4999, debug=True)
