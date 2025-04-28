import os
from logging import getLogger
from typing import List

from pydantic.v1 import BaseSettings
from dotenv import load_dotenv

from src.logging_config import setup_logging

logger = getLogger(__name__)


class AppSettings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    DEBUG_MODE: bool = False

    OPENAI_API_KEY: str
    OPENROUTER_API_KEY: str
    LANGUAGE_MODEL: str = "openai/gpt-4"

    LINE_CHANNEL_SECRET: str
    LINE_CHANNEL_ACCESS_TOKEN: str

    SYSTEM_PROMPT: str = (
        "You are a helpful tutor that provides detailed step-by-step solutions to academic problems. "
        "Always break down complex problems into smaller, manageable steps. "
        "Explain each step clearly and concisely. "
        "If relevant, include mathematical formulas, scientific principles, or theoretical concepts. "
        "End with a brief summary of the solution."
    )


# Initialize settings
load_dotenv()
app_settings = AppSettings()
