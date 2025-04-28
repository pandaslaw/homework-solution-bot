import os
from logging import getLogger
from typing import List

import yaml
from pydantic.v1 import BaseSettings
from dotenv import load_dotenv

from src.logging_config import setup_logging

logger = getLogger(__name__)


class AppSettings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    DEBUG_MODE: bool = False
    OPENROUTER_API_KEY: str
    LANGUAGE_MODEL: str = "openai/gpt-4o-mini"  # Supports both text and image inputs
    MAX_TOKENS: int = 2000
    RESPONSE_LANGUAGE: str = "English"  # Change to "Japanese" in production

    LINE_CHANNEL_SECRET: str
    LINE_CHANNEL_ACCESS_TOKEN: str

    # Image processing settings
    MAX_IMAGE_SIZE: int = 4096  # Maximum image dimension
    MAX_PROBLEMS_PER_IMAGE: int = 1
    ALLOWED_IMAGE_FORMATS: List[str] = ["jpg", "jpeg", "png"]

    # Prompts will be loaded from YAML
    SYSTEM_PROMPT: str = ""
    IMAGE_SYSTEM_PROMPT: str = ""

    def load_prompts_from_yaml(self, yaml_file="prompts.yaml"):
        """Load prompts from the specified YAML file."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        docs_dir = "docs"
        yaml_file_full_path = os.path.join(root_dir, docs_dir, yaml_file)

        try:
            with open(yaml_file_full_path, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file)

            self.SYSTEM_PROMPT = prompts.get("system_prompt", "")
            self.IMAGE_SYSTEM_PROMPT = prompts.get("image_system_prompt", "")
            logger.info("Successfully loaded prompts from YAML file")
        except Exception as e:
            logger.error(f"Error loading prompts from YAML: {str(e)}", exc_info=True)
            raise


# Initialize settings
load_dotenv()
app_settings = AppSettings()

# Load prompts
app_settings.load_prompts_from_yaml()
