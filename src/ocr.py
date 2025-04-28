"""OCR module for processing images containing homework problems."""
import os
import tempfile
from logging import getLogger
from typing import Optional
from io import BytesIO

import aiohttp
from PIL import Image

from src.config import app_settings
from src.bot import generate_answer

logger = getLogger(__name__)


async def download_image(image_url: str) -> Optional[str]:
    """Download image from URL and save to temp file."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    logger.error(f"Error downloading image: HTTP {response.status}")
                    return None

                # Get file extension from content type
                content_type = response.headers.get('content-type', '')
                ext = content_type.split('/')[-1]
                if ext not in app_settings.ALLOWED_IMAGE_FORMATS:
                    logger.error(f"Unsupported image format: {ext}")
                    return None

                # Save to temp file
                temp_dir = tempfile.gettempdir()
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}', dir=temp_dir)
                temp_file.write(await response.read())
                temp_file.close()

                return temp_file.name

    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}", exc_info=True)
        return None


async def count_problems_in_image(image_bytes: bytes) -> int:
    """Count the number of homework problems in the image"""
    try:
        image = Image.open(BytesIO(image_bytes))
        # TODO: Implement problem counting logic
        # For now, assume 1 problem per image
        return 1
    except Exception as e:
        logger.error(f"Error counting problems in image: {str(e)}")
        return 1


async def process_image(image_bytes: bytes) -> Optional[str]:
    """Process the image and extract text/information from it"""
    try:
        # TODO: Implement actual OCR
        # For now, just return a placeholder
        return "[Image content would be processed here]"
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return None


async def process_image_and_generate_answer(image_bytes: bytes) -> str:
    """Process image bytes and generate an answer"""
    try:
        # Count problems in the image
        problem_count = await count_problems_in_image(image_bytes)
        if problem_count > 1:
            return "I can only handle one problem at a time. Please send a single problem."

        # Process the image
        processed_text = await process_image(image_bytes)
        if not processed_text:
            return "Sorry, I couldn't process the image. Please try again."

        # Generate answer using the processed text
        return await generate_answer(processed_text)

    except Exception as e:
        logger.error(f"Error in process_image_and_generate_answer: {str(e)}")
        return "Sorry, something went wrong while processing your image. Please try again."


async def process_image_file(image_path: str) -> Optional[str]:
    """Process image for better OCR results."""
    try:
        # Open and resize image if needed
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if too large
            if max(img.size) > app_settings.MAX_IMAGE_SIZE:
                ratio = app_settings.MAX_IMAGE_SIZE / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)

            # Save processed image
            temp_dir = tempfile.gettempdir()
            processed_path = os.path.join(temp_dir, f"processed_{os.path.basename(image_path)}")
            img.save(processed_path, 'JPEG', quality=95)

            return processed_path

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        return None
    finally:
        # Clean up temp file
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temp file: {str(e)}")


async def count_problems_in_image(image_path: str) -> int:
    """Count number of problems in image. Currently returns 1 for simplicity."""
    # TODO: Implement actual problem counting using AI
    # TODO: Implement problem counting logic
    # For now, assume one problem per image
    return 1
