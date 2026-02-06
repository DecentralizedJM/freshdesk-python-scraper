import os
import json
import logging
from typing import Dict, Tuple, Optional

# Prefer new Google GenAI SDK (https://ai.google.dev/gemini-api/docs/quickstart)
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
try:
    import google.generativeai as genai_legacy
    HAS_GEMINI_LEGACY = True
except ImportError:
    HAS_GEMINI_LEGACY = False

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
        
        if GEMINI_API_KEY and HAS_GENAI:
            self.mode = "gemini"
            # Client picks up GEMINI_API_KEY from env per quickstart
            self._genai_client = genai.Client()
            print("AI Processor: Using Google Gemini (google.genai).")
        elif GEMINI_API_KEY and HAS_GEMINI_LEGACY:
            self.mode = "gemini"
            genai_legacy.configure(api_key=GEMINI_API_KEY)
            self._genai_legacy_model = genai_legacy.GenerativeModel('gemini-1.5-flash')
            print("AI Processor: Using Google Gemini (legacy google.generativeai).")
            
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
        system_instruction = f"""
        You are an intelligent ticket classification agent.
        Your goal is to determine if a customer support ticket matches the user's search intent.
        
        USER INTENT: "{intent}"
        
        RULES:
        1. "relevant": true if the ticket discusses the intent (even vaguely). false if completely unrelated.
        2. "summary": A concise 1-sentence summary of the user's specific problem/request in the ticket.
        """
        prompt = f"""
        Analyze this ticket content:
        ---
        {self._truncate_text(text)}
        ---
        
        Return JSON only.
        """
        try:
            if hasattr(self, "_genai_client"):
                # Google GenAI SDK: https://ai.google.dev/gemini-api/docs/quickstart
                response = self._genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                    ),
                )
                return self._parse_json_response(response.text)
            else:
                # Legacy google.generativeai
                model = genai_legacy.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction,
                )
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"},
                )
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
