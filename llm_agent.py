#Install Flask and OpenAI : # pip install Flask openai flask-cors 

import json
from flask import jsonify
from openai import OpenAI
from typing import Dict, Any

class OpenAIService:

    '''
    A wrapper around the OpenAI client to handle all LLM interactions in one place.
    '''

    # Initialize the OpenAI client with the provided API key and model
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):  # Replace with o3 or o4 later (More token expensive so please don't use it for now)
        self.client = OpenAI(api_key=api_key)
        self.model = model

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
            temperature = 0 # Lower temperature for more deterministic output (Play around with this value)
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
   

   
    # def score_reliability(self, info: Dict[str, Any]) -> Dict[str, Any]:
    #     '''
    #     Given the extracted fields, asks the LLM to rate reliability on a scale 1-5
    #     and return a JSON with:
    #       - score: int
    #       - explanation: str
    #     '''
    #     prompt = (
    #         f"Given the following extracted article information:\n"
    #         f"Topic: {info.get('topic')}\n"
    #         f"Claims: {info.get('claims')}\n"
    #         f"Data: {info.get('data')}\n"
    #         f"Intent: {info.get('intent')}\n\n"
    #         "Assess the reliability of this article on a scale from 1 (not reliable) to 5 (very reliable)."
    #         " Return only a JSON object with keys 'score' and 'explanation'."
    #     )
    #     resp = self.client.chat.completions.create(
    #         model=self.model,
    #         messages=[{"role": "user", "content": prompt}],
    #         temperature=0
    #     )
    #     return json.loads(resp.choices[0].message.content)
