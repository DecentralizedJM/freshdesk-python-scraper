import os
import json
import logging
from typing import Dict, Tuple, Optional

# Attempt imports, but don't crash if missing (though we installed them)
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from config import GEMINI_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

class TicketAnalyzer:
    def __init__(self):
        self.mode = "keyword"
        self.model = None
        
        if GEMINI_API_KEY and HAS_GEMINI:
            self.mode = "gemini"
            genai.configure(api_key=GEMINI_API_KEY)
            self.model_client = genai.GenerativeModel('gemini-1.5-flash')
            print("AI Processor: Using Google Gemini.")
            
        elif OPENAI_API_KEY and HAS_OPENAI:
            self.mode = "openai"
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            print("AI Processor: Using OpenAI.")
        else:
            print("AI Processor: No AI keys found. Using simple keyword fallback.")

    def analyze(self, ticket_text: str, user_intent: str) -> Tuple[bool, str]:
        """
        Analyzes the ticket text against the user intent.
        Returns: (is_relevant: bool, summary: str)
        """
        if not user_intent or not user_intent.strip():
            # If no intent provided, everything is relevant
            return True, "No specific intent provided."

        if self.mode == "keyword":
            return self._analyze_keyword(ticket_text, user_intent)
        elif self.mode == "gemini":
            return self._analyze_gemini(ticket_text, user_intent)
        elif self.mode == "openai":
            return self._analyze_openai(ticket_text, user_intent)
        
        return True, "Error: Unknown mode"

    def _analyze_keyword(self, text: str, intent: str) -> Tuple[bool, str]:
        # Simple fallback: check if intent words are in text
        # This is "dumb" but functional without valid keys
        text_lower = text.lower()
        intent_lower = intent.lower()
        
        # Split intent into words and check if 50% match? Or just direct inclusion?
        # User said "relevant to api", so if "api" in text.
        # But if user says "customer demanding refund", checking for "refund" is good.
        
        words = intent_lower.split()
        match_count = sum(1 for w in words if w in text_lower)
        
        if match_count >= 1: # Very lenient
            return True, f"Contains keywords from intent: '{intent}'"
        else:
            return False, "Does not contain intent keywords."

    def _truncate_text(self, text: str, max_chars=4000) -> str:
        return text[:max_chars] + "..." if len(text) > max_chars else text

    def _analyze_gemini(self, text: str, intent: str) -> Tuple[bool, str]:
        prompt = self._construct_prompt(text, intent)
        try:
            response = self.model_client.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return True, f"AI Error: {str(e)}"

    def _analyze_openai(self, text: str, intent: str) -> Tuple[bool, str]:
        prompt = self._construct_prompt(text, intent)
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # Cost effective
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that classifies support tickets."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            return True, f"AI Error: {str(e)}"

    def _construct_prompt(self, text: str, intent: str) -> str:
        truncated = self._truncate_text(text)
        return f"""
        You are an AI assistant helping a user filter support tickets.
        
        USER INTENT: "{intent}"
        
        TICKET CONTENT:
        "{truncated}"
        
        TASK:
        1. Determine if this ticket is RELEVANT to the User Intent. Ignore spam or unrelated issues.
        2. Provide a 1-sentence summary of the ticket context.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "relevant": boolean,
            "summary": "string"
        }}
        """

    def _parse_json_response(self, response_text: str) -> Tuple[bool, str]:
        try:
            # Clean up potential markdown blocks like ```json ... ```
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            return data.get("relevant", True), data.get("summary", "No summary provided.")
        except json.JSONDecodeError:
            # Fallback if model fails to output JSON
            lower_resp = response_text.lower()
            relevant = "relevant" in lower_resp and "not relevant" not in lower_resp
            # Try to grab the text as summary
            return relevant, response_text[:100]
