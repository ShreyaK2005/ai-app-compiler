from openai import OpenAI
import json
import time
import hashlib
from config.constants import (

    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR
)
from config.constants import OPENAI_API_KEY


from utils.logger import log_info, log_error, log_warning
from openai import OpenAI, RateLimitError, APIError


class LLMClient:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = MODEL
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE

    def call_llm(self, prompt: str, system_prompt: str = None, max_retries: int = MAX_RETRIES) -> str:
        """
        Call Claude API with retry logic.
        Returns raw string response.
        """
        for attempt in range(max_retries):
            try:
                input_text = prompt

                if system_prompt:
                    input_text = f"{system_prompt}\n\n{prompt}"

                response = self.client.responses.create(
                    model=self.model,
                    input=input_text
                )

                text_content = response.output_text

            except RateLimitError as e:
                wait_time = (RETRY_BACKOFF_FACTOR ** attempt) * 2
                log_warning(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

            except RateLimitError as e:
                log_error(f"API Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(RETRY_BACKOFF_FACTOR ** attempt)

        raise Exception(f"Failed after {max_retries} attempts")

    def call_llm_json(self, prompt: str, system_prompt: str = None) -> dict:
        """
        Call Claude and expect JSON response.
        Uses json_repair library to fix malformed JSON.
        """
        from utils.json_parser import parse_json_safe

        response_text = self.call_llm(prompt, system_prompt)

        # Try to extract JSON from response
        json_obj = parse_json_safe(response_text)

        if json_obj is None:
            log_error(f"Could not parse JSON from response: {response_text[:200]}")
            raise ValueError("Invalid JSON response from LLM")

        return json_obj

    def compute_prompt_hash(self, prompt: str) -> str:
        """Compute hash of prompt for consistency tracking"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]