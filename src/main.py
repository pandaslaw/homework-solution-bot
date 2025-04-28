import os
import tempfile
from logging import getLogger
import inspect
import asyncio
from typing import Callable, Dict, List, Type, Union

from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    AsyncMessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    Configuration
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    Event
)

from src.config import app_settings
from src.llm import generate_answer
from src.bot import process_image_and_generate_answer
from src.logging_config import setup_logging

# Setup logging
setup_logging()
logger = getLogger(__name__)


class AsyncWebhookHandler(WebhookHandler):
    def __init__(self, channel_secret):
        super().__init__(channel_secret)
        self._handlers: Dict[str, List[Callable]] = {}

    def add(self, event_type: Type[Event], message=None):
        def decorator(func: Callable):
            if not asyncio.iscoroutinefunction(func):
                raise ValueError(f"Handler {func.__name__} must be async")
            
            key = self._WebhookHandler__get_handler_key(event_type, message)
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(func)
            return func
        return decorator

    async def handle(self, body: str, signature: str):
        """Handle webhook asynchronously"""
        # self.verify_signature(body.encode('utf-8'), signature)
        
        events = self.parser.parse(body, signature)
        results = []
        
        for event in events:
            func = None
            key = None
            
            for t in inspect.getmro(type(event)):
                if t == Event or t == object:
                    break
                
                key = self._WebhookHandler__get_handler_key(
                    t,
                    type(event.message) if hasattr(event, 'message') else None
                )
                
                if key in self._handlers:
                    func = self._handlers[key][0]
                    break
            
            if func is None:
                logger.warning(f'No handler found for {key}')
                continue

            try:
                result = await func(event)
                results.append(result)
            except Exception as e:
                logger.error(f'Error occurred while handling event: {str(e)}', exc_info=True)
                raise

        return results


logger.info("Initializing LINE bot application...")
app = FastAPI()

# LINE API setup
configuration = Configuration(access_token=app_settings.LINE_CHANNEL_ACCESS_TOKEN)
line_bot_api = AsyncMessagingApi(AsyncApiClient(configuration))
line_bot_blob_api = AsyncMessagingApiBlob(AsyncApiClient(configuration))
handler = AsyncWebhookHandler(app_settings.LINE_CHANNEL_SECRET)
logger.info("LINE bot credentials configured successfully")


@app.post("/callback")
async def callback(request: Request):
    logger.info("Received webhook callback from LINE")
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    body_text = body.decode('utf-8')
    
    try:
        await handler.handle(body_text, signature)
        return 'OK'
    except InvalidSignatureError:
        logger.error("Invalid signature in LINE webhook callback")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@handler.add(MessageEvent, message=TextMessageContent)
async def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    logger.info(f"Received text message from user {user_id}: {user_message}")

    try:
        solution = await generate_answer(user_message)
        logger.info(f"Generated solution for user {user_id}")
        logger.debug(f"Solution content length: {len(solution)}")
        
        # Send the solution back to the user
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=solution)]
            )
        )
        logger.info(f"Successfully sent solution to user {user_id}")
    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {str(e)}", exc_info=True)
        # Try to send error message to user
        try:
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Sorry, I encountered an error. Please try again later.")]
                )
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id}: {str(send_error)}")


@handler.add(MessageEvent, message=ImageMessageContent)
async def handle_image_message(event):
    user_id = event.source.user_id
    logger.info(f"Received image message from user {user_id}")

    try:
        # Get image content using AsyncMessagingApiBlob
        message_id = event.message.id
        image_bytes = await line_bot_blob_api.get_message_content(message_id)

        # Process image bytes directly and generate solution
        solution = await process_image_and_generate_answer(image_bytes)
        logger.info(f"Generated solution from image for user {user_id}")
        logger.debug(f"Solution content length: {len(solution)}")

        # Send the solution back to the user
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=solution)]
            )
        )
        logger.info(f"Successfully sent solution to user {user_id}")
    except Exception as e:
        logger.error(f"Error processing image from user {user_id}: {str(e)}", exc_info=True)
        # Try to send error message to user
        try:
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Sorry, I couldn't process your image. Please try again.")]
                )
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id}: {str(send_error)}")
