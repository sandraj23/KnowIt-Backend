# llm_agent_local.py
# ─────────────────────────────────────────────────
# Dependencies: pip install flask flask-cors newspaper3k ollama

import os
import json
import re
import requests
from newspaper import Article
import ollama
from typing import Dict, Any, List


def fetch_article_text(url: str, timeout: float = 5.0) -> str:
    """
    Download & parse article text with Newspaper3k, then fallback to a safe HTTP GET.
    In all cases of failure (timeouts, 403s, parsing errors), return an empty string.
    """
    # 1) Try Newspaper3k
    try:
        art = Article(url)
        art.download()
        art.parse()
        text = art.text or ""
        return text
    except Exception as e:
        print(f"⚠️ Newspaper3k parsing failed for {url}: {e}")

    # 2) Fallback plain HTTP GET
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.text or ""
    except Exception as e:
        # swallow everything: timeouts, 403, 404, etc.
        print(f"⚠️ HTTP fallback failed for {url}: {e}")
        return "-1"

def perform_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a web search via Google Custom Search API and return up to `num_results` items.
    Requires environment variables:
      - GOOGLE_CSE_API_KEY: Your Google API key
      - GOOGLE_CSE_ID: Your Custom Search Engine ID

    Returns:
      List of dicts with keys: 'title', 'url', 'snippet'.
    """
    if not api_key or not cse_id:
        raise EnvironmentError("Please set GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables.")

    endpoint = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": num_results
    }
    resp = requests.get(endpoint, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []


    for item in data.get("items", []):
        results.append({
            "title":   item.get("title"),
            "url":     item.get("link"),
            "snippet": item.get("snippet")
        })
    return results


class OllamaService:
    """
    Local LLM service backed by the Ollama CLI.
    """

    def __init__(self, api_key: str = None, model: str = "mistral"):
        # The api_key argument is ignored for local usage.
        self.model = model
        # Pull model locally if needed
        try:
            ollama.pull(self.model)
        except Exception:
            pass

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Send a chat completion request to the local Ollama model.
        """
        resp = ollama.chat(model=self.model, messages=messages)
        return resp.get("message", {}).get("content", "").strip()

    def assess_phishing(self, content: str) -> Dict[str, Any]:
        """
        Given email text, rate phishing sense 1–5 and explain.
        """
        prompt = (
            f"Given the following email content:\n{content}\n\n"
            "Assess the phishing sense of this email on a scale from 1 (low) to 5 (high). "
            "Return only a JSON object with keys 'phishingSense' and 'explanation'."
        )
        raw = self._chat([{"role": "user", "content": prompt}])
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(cleaned)

    def extract_article_content(self, html_content: str) -> Dict[str, Any]:
        """
        Extract 'topic', 'claims', and 'intent' from article HTML/text.
        Returns a dict with those keys.
        """
        prompt = (
            "Extract the following from the article below as JSON keys 'topic', 'claims', and 'intent':\n\n"
            f"{html_content}\n\n"
            "For the topic, use the main subject of the article.\n"
            "Make sure the topic is detailed and specific.\n"
            "For claims, use a list of claims made in the article.\n"
            "For intent, use a sentence or short phrase that summarizes the article's purpose.\n\n"
            "Ensure the JSON is valid. Return only the JSON object without additional text."
        )
        raw = self._chat([{"role": "user", "content": prompt}])
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(cleaned)

    def search_and_compare(
        self,
        topic: str,
        intent: str,
        original_claims: List[str],
        num_results: int = 4
    ) -> Dict[str, Any]:
        """
        Search topic+intent, then for each result extract key claims and have the LLM
        generate both a similarity 'score' (1–5) and a one-sentence 'explanation'.
        Returns {search_query, results:[{title,url,new_claims,score,explanation}]}
        """
        query = f"{topic} {intent}"
        enriched = []
        loop = num_results
        for item in perform_search(query, loop):
            if(item == "-1"):
                loop += 1

            title, url = item['title'], item['url']
            text = fetch_article_text(url)
            if not text:
                continue
            # Build prompt for claims + score + explanation
            prompt = (
                "Original claims: " + json.dumps(original_claims) + "\n"
                "Article text: " + text + "\n\n"
                "Extract key claims under 'claims' (list), rate overall similarity to the original claims"
                " on a scale 1–5 under 'score' with 1 being not similar and 5 being similar, and provide a short one-sentence 'explanation' for that score."
                " Return exactly: {\"claims\": [...], \"score\": <int>, \"explanation\": \"...\"}"
            )
            raw = self._chat([{"role":"user","content":prompt}])
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            try:
                parsed = json.loads(cleaned)
                new_claims = parsed.get("claims", [])
                score = parsed.get("score", None)
                explanation = parsed.get("explanation", "")
            except Exception as e:
                print(f"⚠️ search_and_compare parse error: {e}\nRaw: {cleaned}")
                new_claims, score, explanation = [], None, ""

            enriched.append({
                "title": title,
                "url": url,
                # "new_claims": new_claims,
                "score": score,
                "explanation": explanation
            })
        return {"search_query": query, "results": enriched}
