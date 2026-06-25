import os
import time
import hashlib
import json
from config.constants import MAX_RETRIES, RETRY_BACKOFF_FACTOR
from utils.logger import log_info, log_error, log_warning, log_debug


class LLMClient:
    def __init__(self):
        """Initialize Groq client"""
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Groq not installed. Run: pip install groq")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"
        log_info(f"Initialized Groq client with model: {self.model}")

    def call_llm(self, prompt: str, system_prompt: str = None, max_retries: int = MAX_RETRIES) -> str:
        """
        Call Groq API with retry logic and better error handling.
        Returns raw string response.
        """
        for attempt in range(max_retries):
            try:
                messages = []

                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                messages.append({"role": "user", "content": prompt})

                log_debug(f"Calling Groq (attempt {attempt + 1}/{max_retries})...")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096,
                    top_p=1.0
                )

                text_content = response.choices[0].message.content
                log_info(f" Groq call successful on attempt {attempt + 1}")
                return text_content

            except Exception as e:
                error_msg = str(e)

                if "429" in error_msg or "rate" in error_msg.lower():
                    wait_time = (RETRY_BACKOFF_FACTOR ** attempt) * 2
                    log_warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                elif attempt == max_retries - 1:
                    log_error(f"Final attempt failed: {error_msg}")
                    raise
                else:
                    log_warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    time.sleep(RETRY_BACKOFF_FACTOR ** attempt)

        raise Exception(f"Failed after {max_retries} attempts")

    def call_llm_json(self, prompt: str, system_prompt: str = None) -> dict:
        """
        Call Groq and expect JSON response.
        Handles parsing and repair automatically.
        """
        from utils.json_parser import parse_json_safe

        response_text = self.call_llm(prompt, system_prompt)

        log_debug(f"Raw response (first 200 chars): {response_text[:200]}")

        # Try to parse JSON
        json_obj = parse_json_safe(response_text)

        if json_obj is None:
            log_error(f"Could not parse JSON from response")
            log_debug(f"Full response: {response_text}")
            raise ValueError("Invalid JSON response from LLM")

        log_debug(f"Successfully parsed JSON with keys: {list(json_obj.keys())}")
        return json_obj

    def compute_prompt_hash(self, prompt: str) -> str:
        """Compute hash of prompt for consistency tracking"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
