import datetime as dt
import json
from logging import getLogger

from openai import OpenAI

from src.config import app_settings

logger = getLogger(__name__)


def generate_answer(user_input: str) -> str:
    """
    Calls LLM using system prompt and user's text message.
    """
    # return "output"
    if not user_input:
        logger.info("User input is empty. SKIPPING")
        return ""

    start_time = dt.datetime.now()
    system_prompt = app_settings.SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please solve this problem step by step: {user_input}"},
    ]

    logger.info(f"USER PROMPT: '{user_input}'")
    logger.info("Generating LLM response... ")

    # Primary: Use OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=app_settings.OPENROUTER_API_KEY,
        http_client=None  # Don't use custom HTTP client
    )

    try:
        response = client.chat.completions.create(
            model=app_settings.LANGUAGE_MODEL,
            messages=messages
        )
    except Exception as e:
        logger.error(f"OpenRouter API call failed: {e}", exc_info=True)
        logger.info("Falling back to OpenAI API...")
        
        # Fallback: Use OpenAI
        try:
            client = OpenAI(
                api_key=app_settings.OPENAI_API_KEY,
                http_client=None  # Don't use custom HTTP client
            )
            model = app_settings.LANGUAGE_MODEL.split('/')[-1]
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            return "Sorry, I couldn't generate a solution at the moment. Please try again."

    if response.choices and len(response.choices) > 0:
        output = response.choices[0].message.content
    else:
        logger.error(
            "Request to LLM failed: no answer was generated. "
            f"Check the input and try again."
        )
        logger.info(f"API Response: {json.dumps(response, indent=4)}")
        return "Sorry, I couldn't generate a solution at the moment. Please try again."

    usage = response.usage
    logger.info(
        f"NUMBER OF TOKENS used per OpenAI API request: {usage.total_tokens}. "
        f"System prompt: {usage.prompt_tokens}. "
        f"Generated response: {usage.completion_tokens}."
    )
    running_secs = (dt.datetime.now() - start_time).microseconds
    logger.info(f"Answer generation took {running_secs / 100000:.2f} seconds.")

    return output
