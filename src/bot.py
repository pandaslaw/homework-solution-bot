import base64
import datetime as dt
from logging import getLogger

from src.config import app_settings
from src.llm import call_openrouter, format_line_message, format_solution

logger = getLogger(__name__)

async def process_image_and_generate_answer(image_bytes: bytes) -> str:
    """
    Process image bytes and generate answer using OpenRouter's GPT-4o mini.
    """
    try:
        # Encode image bytes for API
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        start_time = dt.datetime.now()
        system_prompt = app_settings.IMAGE_SYSTEM_PROMPT.format(RESPONSE_LANGUAGE=app_settings.RESPONSE_LANGUAGE)

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this problem and provide a step-by-step solution:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        answer = await call_openrouter(messages)
        
        # Format the response
        formatted_answer = format_solution(answer)
        
        return formatted_answer
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        return "Sorry, I encountered an error while processing your image. Please try again or send the problem as text."
