from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from logging import getLogger

from src.config import app_settings
from src.bot import generate_answer
from src.logging_config import setup_logging

# Setup logging
setup_logging()
logger = getLogger(__name__)

logger.info("Initializing LINE bot application...")
app = Flask(__name__)

# LINE API setup
configuration = Configuration(access_token=app_settings.LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(app_settings.LINE_CHANNEL_SECRET)
logger.info("LINE bot credentials configured successfully")

@app.route("/callback", methods=['POST'])
def callback():
    logger.info("Received webhook callback from LINE")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
        logger.debug(f"Successfully handled webhook. Body length: {len(body)}")
    except InvalidSignatureError:
        logger.error("Invalid signature in LINE webhook callback")
        abort(400)
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        abort(500)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    logger.info(f"Received message from user {user_id}: {user_message}")

    try:
        solution = generate_answer(user_message)
        logger.info(f"Generated solution for user {user_id}")
        logger.debug(f"Solution content length: {len(solution)}")
        
        # Send the solution back to the user
        line_bot_api.reply_message(
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
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Sorry, I encountered an error. Please try again later.")]
                )
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id}: {str(send_error)}")

if __name__ == "__main__":
    port = int(app_settings.PORT if hasattr(app_settings, 'PORT') else 5000)
    logger.info(f"Starting LINE bot server on port {port}")
    app.run(host="0.0.0.0", port=port)
