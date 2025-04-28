from logging import getLogger
import asyncio
import datetime as dt
from typing import Optional, List, Dict, Any

from openai import AsyncOpenAI

from src.config import app_settings

logger = getLogger(__name__)


def create_openrouter_client() -> AsyncOpenAI:
    """Create OpenRouter client with proper configuration."""
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=app_settings.OPENROUTER_API_KEY,
        http_client=None  # Don't use custom HTTP client
    )


async def call_openrouter(messages: List[Dict[str, Any]], max_retries: int = 2) -> str:
    """Call OpenRouter API with retry logic."""
    client = create_openrouter_client()
    
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=app_settings.LANGUAGE_MODEL,
                messages=messages,
                max_tokens=app_settings.MAX_TOKENS
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"OpenRouter API call failed after {max_retries} attempts: {e}", exc_info=True)
                return "Sorry, I encountered an error. Please try again later."
            logger.warning(f"OpenRouter API call attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(1)  # Wait before retrying
    
    return "Sorry, I encountered an error. Please try again later."


async def generate_answer(user_input: str) -> str:
    """Generate an answer using OpenRouter"""
    if not user_input:
        logger.info("User input is empty. SKIPPING")
        return ""

    start_time = dt.datetime.now()
    system_prompt = app_settings.SYSTEM_PROMPT.format(RESPONSE_LANGUAGE=app_settings.RESPONSE_LANGUAGE)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please solve this problem step by step: {user_input}"},
    ]

    logger.info(f"USER PROMPT: '{user_input}'")
    logger.info("Generating LLM response... ")

    answer = await call_openrouter(messages)
    
    end_time = dt.datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Answer generation took {duration:.2f} seconds.")

    return answer
