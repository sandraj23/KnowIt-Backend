#Install Flask and OpenAI : # pip install Flask openai flask-cors 

import json
import re
import requests
from flask import jsonify
from openai import OpenAI
from typing import Dict, Any, List
from newspaper import Article
import requests

def fetch_article_text(url: str, timeout: float = 5.0) -> str:
    """
    Download & parse the main text of an article.
    Falls back to raw HTML if parsing fails.
    """
    try:
        art = Article(url)
        art.download()
        art.parse()
        return art.text
    except Exception:
        # fallback to grabbing raw HTML
        resp = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text


# --- Web search implementation using Google Custom Search JSON API ---
def perform_search(query, num_results) -> List[Dict[str, str]]:
    '''
    Perform a web search via Google Custom Search API and return up to `num_results` items.
    Requires environment variables:
      - GOOGLE_CSE_API_KEY: Your Google API key
      - GOOGLE_CSE_ID: Your Custom Search Engine (CSE) ID

    Returns a list of dicts with keys: 'title', 'url', and 'snippet'.
    '''
    api_key = 'AIzaSyBzMwB74bQv-I5s89f55RJdNdbXvwclMwU'
    cse_id = 'd54dc2607535a4fbb'
    if not api_key or not cse_id:
        raise EnvironmentError("Please set GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables.")

    endpoint = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": num_results
    }

    resp = requests.get(endpoint, params=params)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet")
        })
    return results

class OpenAIService:

    '''
    A wrapper around the OpenAI client to handle all LLM interactions in one place.
    '''

    # Initialize the OpenAI client with the provided API key and model
    def __init__(self, api_key: str, model: str = "o3"):  # Replace with o3 or o4 later (More token expensive so please don't use it for now)
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def evaluate_article_metadata(self, title: str, authors: str, content: str) -> Dict[str, Any]:
        """
        Evaluate the article metadata and return a JSON object answering the following questions:
            1. The author specifies the researcher/s who conducted the original study
            2. The article includes references, citations, and links to support their claims
            3. The article is written fairly and neutrally and is free from exaggeration
            4. You can find the original study based on the information provided
            5. You know how many people participated in the original study
            6. You can make reasonable conclusions from the information provided
            7. The article was published by a trustworthy source
            8. The content of the article appears to be accurate, factual, and recent
            9. The article appears to be free from bias and objective
            10. The findings can be supported by other sources
        """
        prompt = (
            "Given the following article metadata:\n"
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Content: {content}\n\n"
            "Evaluate the article based on the following criteria:\n"
            "1. The author specifies the researcher/s who conducted the original study\n"
            "2. The article includes references, citations, and links to support their claims\n"
            "3. The article is written fairly and neutrally and is free from exaggeration\n"
            "4. You can find the original study based on the information provided\n"
            "5. You know how many people participated in the original study\n"
            "6. You can make reasonable conclusions from the information provided\n"
            "7. The article was published by a trustworthy source\n"
            "8. The content of the article appears to be accurate, factual, and recent\n"
            "9. The article appears to be free from bias and objective\n"
            "10. The findings can be supported by other sources\n\n"
            "Return a JSON object with keys and boolean values: \n"
            "specifies_researcher, includes_references, written_fairly, "
            "find_original_study, know_participants, make_conclusions, "
            "published_trustworthy, content_accurate, free_from_bias, "
            "findings_supported\n\n"
            "Ensure the JSON is valid and parsable. Use the following format:\n"
            "{\n"
            "  \"specifies_researcher\": ...,\n"
            "  \"includes_references\": ...,\n"
            "  \"written_fairly\": ...,\n"
            "  \"find_original_study\": ...,\n"
            "  \"know_participants\": ...,\n"
            "  \"make_conclusions\": ...,\n"
            "  \"published_trustworthy\": ...,\n"
            "  \"content_accurate\": ...,\n"
            "  \"free_from_bias\": ...,\n"
            "  \"findings_supported\": ...\n"
            "}\n\n"
            "Return only the JSON object without any additional text."
        )

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            # temperature=0
        )

        # Parse the response and return it
        llm_output_raw = response.choices[0].message.content.strip()

        try :
            parsed = json.loads(llm_output_raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON output: {e} Output was: {llm_output_raw}")
        # Validate keys
        required = {
            "specifies_researcher", "includes_references", "written_fairly",
            "find_original_study", "know_participants", "make_conclusions",
            "published_trustworthy", "content_accurate", "free_from_bias",
            "findings_supported"
        }
        keys = set(parsed.keys())
        if not required.issubset(keys):
            missing = required - keys
            raise ValueError(f"LLM output missing keys: {missing} Output was: {parsed}")
        # Normalize keys to lowercase and return
        return {k.lower(): parsed[k] for k in required}




    # Based on email content, this function will return a JSON with:
    # - phishingSense: int (1-5)
    # - explanation: str
    def evaluate_phishing(self, content: str) -> Dict[str, Any]:
        '''
        Given the email content, asks the LLM to rate phishing sense on a scale 1-5
        and return a JSON with:
            - phishingSense: 1-5
            - explanation: str
        '''
        prompt = (
            f"Given the following email content:\n{content}\n\n"
            "Assess the phishing sense of this email on a scale from 1 (low) to 5 (high)."
            " Return only a JSON object with keys 'phishingSense' and 'explanation'."
            "Ensure the JSON is valid and parsable. Use the following format:\n"
            "{\n"
            "  \"phishingSense\": \"...\",\n"
            "  \"explanation\": \"...\"\n"
            "}\n\n"
            "Return only the JSON object without any additional text."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            # temperature=0
        )
        # Parse the response and return it
        llm_output_raw = resp.choices[0].message.content.strip()
        # Log the raw output for debugging
        print(f"LLM raw output: {llm_output_raw}")
        try:
            parsed = json.loads(llm_output_raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON output: {e} Output was: {resp.choices[0].message.content}")
        # Validate keys
        print(f"Parsed LLM output: {parsed}")
        required = {"phishingSense", "explanation"}
        keys = set(parsed.keys())
        if not required.issubset(keys):
            missing = required - keys
            raise ValueError(f"LLM output missing keys: {missing} Output was: {parsed}")
        # Normalize keys to lowercase and return
        print({k.lower(): parsed[k] for k in required})
        return {k.lower(): parsed[k] for k in required}

    # Extract article content using the LLM
    def extract_article_content(self, html_content: str) -> Dict[str, Any]:
        
        '''
        Sends the article HTML to the LLM and returns a dict with lowercase keys:
          - topic: str
          - claims: List[str]
          - data: List[str]
          - intent: str
        '''

        # Build prompt for LLM extraction
        prompt = (
            "Extract the following from the article below as a JSON object with keys 'topic', 'claims', 'data' (numeric data), and 'intent':\n\n"
            f"{html_content}\n\n"  
            "Ensure the JSON is valid and parsable. Use the following format:\n"
            "For the topic, use the main subject of the article.\n"
            "Make sure the topic is detailed and specific.\n"
            "For claims, use a list of claims made in the article.\n"
            "For data, use a list of numeric data points or statistics mentioned in the article.\n"
            "For intent, use a sentence or short phrase that summarizes the article's purpose.\n\n"
            "{\n"
            "  \"topic\": \"...\",\n"
            "  \"claims\": [\"...\", ...],\n"
            "  \"data\": [\"...\", ...],\n"
            "  \"intent\": \"...\"\n"
            "}\n\n"
            "Return only the JSON object without any additional text."
        )

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model = self.model,
            messages = [{"role": "user", "content": prompt}],
            # temperature = 0.2 # Lower temperature for more deterministic output (Play around with this value)
        )

        # Check if response is valid
        llm_output_raw = response.choices[0].message.content.strip()

        # Parse JSON from LLM
        try:
            parsed = json.loads(llm_output_raw)
        
        # If JSON parsing fails, raise a ValueError with the raw output
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON output: {e} Output was: {llm_output_raw}")

        # Validate keys
        required = {"topic", "claims", "data", "intent"}

        # Check if all required keys are present
        keys = set(parsed.keys())

        # If any required keys are missing, raise a ValueError with the missing keys
        if not required.issubset(keys):
            missing = required - keys
            raise ValueError(f"LLM output missing keys: {missing}Output was: {parsed}")

        # Normalize keys to lowercase and return
        return {k.lower(): parsed[k] for k in required}

    # def search_and_compare(self, topic: str, intent: str, original_claims: List[str], num_results: int = 5) -> Dict[str, Any]:
    #     '''
    #     Searches for articles matching topic + intent, extracts their claims, and
    #     classifies each claim as similar or different to the original.

    #     Returns a dict with the schema:
    #     {
    #     "search_query": "<query>",
    #     "results": [
    #         {
    #         "title": "...",
    #         "url": "...",
    #         "claims": [...],
    #         "similar_claims": [...],
    #         "different_claims": [...]
    #         },
    #         ...
    #     ]
    #     }
    #     '''

    #     print("\n==== Inside search_and_compare ====")
    #     # >>> Simplify the query (no more embedding original_claims in it)
    #     query = f"{topic} {original_claims} {intent}"

    #     #print(f"Query to search: {query}")
    #     raw_results = perform_search(query, num_results)
    #     #print(f"perform_search returned {len(raw_results)} results!")

    #     enriched = []
    #     for r in raw_results:
    #         url   = r["url"]
    #         title = r["title"]

    #         # >>> 2a) Fetch the article text
    #         try:
    #             article_text = fetch_article_text(url)
    #         except Exception as e:
    #             print(f"⚠️  Failed to fetch {url}: {e}")
    #             continue

    #         # >>> 2b) Extract its claims via your LLM wrapper
    #         try:

    #             # info  = self.extract_article_content(article_text)


    #             prompt = (
    #                 "You are a research assistant. Original Article Context:\n"
    #                 f"Topic: {topic}\n"
    #                 "Claims:\n"
    #             )
    #             for claim in original_claims:
    #                 prompt += f"- {claim}\n"
    #             prompt += (
    #                 f"Intent: {intent}\n\n"
    #                 "Here is the new article to analyze and compare:\n\n"
    #                 f"{article_text}\n\n"
    #                 "For this article, extract its main claims"
    #                 ", compare them with the "
    #                 "original claims, and classify each as 'similar' or 'different'. "
    #                 "Make sure to split similar claims from different claims.\n\n"
    #                 "Make sure to be lenient regarding the similarity of claims since different articles tend to discuss different points of arguments.\n\n"
    #                 "Similar claims should be closely related to the originals.  If a "
    #                 "claim is similar but not identical, still classify it as 'similar'.\n\n"
    #                 "Return only valid JSON in this schema:\n"
    #                 "{\n"
    #                 "  \"results\": [\n"
    #                 "    {\n"
    #                 "      \"title\": \"<same as input>\",\n"
    #                 "      \"url\": \"<same as input>\",\n"
    #                 "      \"claims\": [...],\n"
    #                 "      \"similar_claims\": [...],\n"
    #                 "      \"different_claims\": [...]\n"
    #                 "    }\n"
    #                 "  ]\n"
    #                 "}\n"
    #             )

    #             # 2) Call the LLM
    #             response = self.client.chat.completions.create(
    #                 model=self.model,
    #                 messages=[{"role": "user", "content": prompt}],
    #                 temperature=0
    #             )
    #             raw_cmp = response.choices[0].message.content.strip()

    #             # 3) Cleanup markdown fences
    #             raw_cmp = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_cmp, flags=re.MULTILINE)
    #             # 4) Drop anything before the first '{'
    #             if "{" in raw_cmp:
    #                 raw_cmp = raw_cmp[ raw_cmp.find("{") : ]

    #             # 5) Parse JSON
    #             parsed = json.loads(raw_cmp)

    #             # 6) Grab the claims array from the first (and only) result
    #             new_claims = parsed.get("results", [])[0].get("claims", []) 
    #             similar = parsed.get("results", [])[0].get("similar_claims", [])
    #             different = parsed.get("results", [])[0].get("different_claims", [])
                
            
    #         except Exception as e:
    #             print(f"⚠️  Failed to extract claims from {url}: {e}")
    #             new_claims = []

    #         # >>> 2c) Classify similar vs. different
    #         # similar   = [c for c in new_claims if c in original_claims]
    #         # different = [c for c in new_claims if c not in original_claims]

    #         enriched.append({
    #             "title":            title,
    #             "url":              url,
    #             "claims":           new_claims,
    #             "similar_claims":   similar,
    #             "different_claims": different
    #         })

    #     # >>> 2d) Return the enriched result set
    #     return {
    #         "search_query": query,
    #         "results":      enriched
    #     }

    def search_and_compare(self, topic: str, intent: str, original_claims: List[str], num_results: int = 10) -> Dict[str, Any]:
        '''
        Searches for articles matching topic + intent, extracts their claims, and
        classifies each claim as similar or different to the original.

        Returns a dict with the schema:
        {
        "search_query": "<query>",
        "results": [
            {
            "title": "...",
            "url": "...",
            "claims": [...],
            "similar_claims": [...],
            "different_claims": [...]
            },
            ...
        ]
        }
        '''

        print("\n==== Inside search_and_compare ====")
        # >>> Simplify the query (no more embedding original_claims in it)
        query = f"{topic} {original_claims} {intent}"

        #print(f"Query to search: {query}")
        raw_results = perform_search(query, num_results)
        #print(f"perform_search returned {len(raw_results)} results!")

        enriched = []
        for r in raw_results:
            url   = r["url"]
            title = r["title"]

            # >>> 2a) Fetch the article text
            try:
                article_text = fetch_article_text(url)
                #print(article_text)
            except Exception as e:
                print(f"⚠️  Failed to fetch {url}: {e}")
                continue

            # >>> 2b) Extract its claims via your LLM wrapper
            try:

                # This Prompt provides the LLM with Context
                prompt = (
                    "You are a research assistant. Original Article Context:\n"
                    f"Topic: {topic}\n"
                    "Claims:\n"
                )
                for claim in original_claims:
                    prompt += f"- {claim}\n"

                # This Prompt Extracts Main Claim from Article
                prompt += (
                    f"Intent: {intent}\n\n"
                    "Here is the new article to analyze:\n\n"
                    f"{article_text}\n\n"
                    "For this article, extract its main claims"
                    "{\n"
                    "  \"results\": [\n"
                    "    {\n"
                    "      \"title\": \"<same as input>\",\n"
                    "      \"url\": \"<same as input>\",\n"
                    "      \"new claims\": [...],\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                )

                # 2) Call the LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                raw_cmp = response.choices[0].message.content.strip()

                # 3) Cleanup markdown fences
                raw_cmp = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_cmp, flags=re.MULTILINE)
                # 4) Drop anything before the first '{'
                if "{" in raw_cmp:
                    raw_cmp = raw_cmp[ raw_cmp.find("{") : ]

                # 5) Parse JSON
                parsed = json.loads(raw_cmp)

                # 6) Grab the claims array from the first (and only) result
                new_claims = parsed.get("results", [])[0].get("new claims", []) 
            
            except Exception as e:
                print(f"⚠️  Failed to extract claims from {url}: {e}")
                new_claims = []

            try:
            

                # This Prompt provides the LLM with Context
                prompt = (
                    "You are a research assistant. Original Article Context:\n"
                    f"Topic: {topic}\n"
                    "Claims:\n"
                )
                for claim in original_claims:
                    prompt += f"- {claim}\n"
                prompt += (
                    f"Intent: {intent}\n\n"
                )

                prompt += (
                    "Here is the new article's claims:\n\n"
                    f"{new_claims}\n\n"
                    "Compare them with the original claims, and classify each as 'similar' or 'different'. "
                    "Make sure to split similar claims from different claims.\n\n"
                    "Make sure to be lenient regarding the similarity of claims since different articles tend to discuss different points of arguments.\n\n"
                    "Similar claims should be closely related to the originals.  If a "
                    "claim is similar but not identical, still classify it as 'similar'.\n\n"
                    "Return only valid JSON in this schema:\n"
                    "{\n"
                    "  \"results\": [\n"
                    "    {\n"
                    "      \"title\": \"<same as input>\",\n"
                    "      \"url\": \"<same as input>\",\n"
                    "      \"similar_claims\": [...],\n"
                    "      \"different_claims\": [...]\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                )

                # 2) Call the LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                raw_cmp = response.choices[0].message.content.strip()

                # 3) Cleanup markdown fences
                raw_cmp = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_cmp, flags=re.MULTILINE)
                # 4) Drop anything before the first '{'
                if "{" in raw_cmp:
                    raw_cmp = raw_cmp[ raw_cmp.find("{") : ]

                # 5) Parse JSON
                parsed = json.loads(raw_cmp)

                # 6) Grab the claims array from the first (and only) result
                similar = parsed.get("results", [])[0].get("similar_claims", [])
                different = parsed.get("results", [])[0].get("different_claims", []) 
            
            except Exception as e:
                print(f"⚠️  Failed to extract claims from {url}: {e}")
                new_claims = []
            # >>> 2c) Classify similar vs. different
            # similar   = [c for c in new_claims if c in original_claims]
            # different = [c for c in new_claims if c not in original_claims]

            enriched.append({
                "title": title,
                "url": url,
                "new claims": new_claims,
                "similar_claims": similar,
                "different_claims": different
            })

        # >>> 2d) Return the enriched result set
        return {
            "search_query": query,
            "results":      enriched
        }





