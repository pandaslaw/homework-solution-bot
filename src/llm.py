from logging import getLogger
import asyncio
import datetime as dt
from typing import Optional, List, Dict, Any, Union, Tuple
import re
import base64
from io import BytesIO
import aiohttp

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


def format_math_expression(latex: str) -> str:
    """Format a LaTeX expression into a more readable text format"""
    # Clean up the LaTeX code
    latex = latex.strip()
    if latex.startswith('\\[') and latex.endswith('\\]'):
        latex = latex[2:-2].strip()
    elif latex.startswith('\\(') and latex.endswith('\\)'):
        latex = latex[2:-2].strip()
    
    # First replace special symbols (before handling braces)
    symbol_replacements = {
        '\\times': '×',
        '\\div': '÷',
        '\\le': '≤',
        '\\ge': '≥',
        '\\neq': '≠',
        '\\approx': '≈',
        '\\pm': '±',
        '\\cdot': '·',
        '_': 'ₓ',
        '^': 'ⁿ',
    }
    
    for old, new in symbol_replacements.items():
        latex = latex.replace(old, new)
    
    # Handle fractions and other brace-based expressions
    def process_braces(expr):
        result = []
        i = 0
        brace_level = 0
        current_cmd = ""
        
        while i < len(expr):
            char = expr[i]
            
            if char == '\\' and i + 1 < len(expr):
                # Start of a LaTeX command
                cmd_end = i + 1
                while cmd_end < len(expr) and expr[cmd_end].isalpha():
                    cmd_end += 1
                current_cmd = expr[i:cmd_end]
                i = cmd_end
                continue
                
            elif char == '{':
                if current_cmd == '\\frac':
                    # Start fraction
                    num_start = i + 1
                    brace_level = 1
                    i += 1
                    while i < len(expr) and brace_level > 0:
                        if expr[i] == '{': brace_level += 1
                        elif expr[i] == '}': brace_level -= 1
                        i += 1
                    num = expr[num_start:i-1]
                    
                    # Get denominator
                    if i < len(expr) and expr[i] == '{':
                        den_start = i + 1
                        brace_level = 1
                        i += 1
                        while i < len(expr) and brace_level > 0:
                            if expr[i] == '{': brace_level += 1
                            elif expr[i] == '}': brace_level -= 1
                            i += 1
                        den = expr[den_start:i-1]
                        result.append(f"({process_braces(num)})/({process_braces(den)})")
                    current_cmd = ""
                    continue
                    
                elif current_cmd == '\\sqrt':
                    # Handle square root
                    sqrt_start = i + 1
                    brace_level = 1
                    i += 1
                    while i < len(expr) and brace_level > 0:
                        if expr[i] == '{': brace_level += 1
                        elif expr[i] == '}': brace_level -= 1
                        i += 1
                    sqrt_content = expr[sqrt_start:i-1]
                    result.append(f"√({process_braces(sqrt_content)})")
                    current_cmd = ""
                    continue
                    
                else:
                    # Skip other braced content
                    brace_level = 1
                    i += 1
                    while i < len(expr) and brace_level > 0:
                        if expr[i] == '{': brace_level += 1
                        elif expr[i] == '}': brace_level -= 1
                        i += 1
                    continue
            
            else:
                result.append(char)
                i += 1
                current_cmd = ""
        
        return ''.join(result)
    
    return process_braces(latex)


def extract_latex_blocks(text: str) -> Tuple[str, List[str]]:
    """Extract LaTeX blocks from text and replace with placeholders"""
    latex_blocks = []
    
    # Find all LaTeX blocks (both inline and display)
    pattern = r'\\[\(\[].*?\\[\)\]]'
    matches = list(re.finditer(pattern, text, re.DOTALL))
    
    # Replace LaTeX blocks with placeholders in reverse order
    # to avoid messing up the positions
    for i, match in enumerate(reversed(matches)):
        latex = match.group(0)
        placeholder = f"__LATEX_{len(matches)-i-1}__"
        latex_blocks.insert(0, latex)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]
    
    return text, latex_blocks


def format_line_message(text: str) -> str:
    """Format text for LINE message, handling headers and line breaks"""
    lines = text.split('\n')
    formatted_lines = []

    for i, line in enumerate(lines):
        # Convert markdown headers to plain text
        if line.strip().startswith('#'):
            # Remove # symbols and get the header text
            header_text = line.lstrip('#').strip()
            if header_text.startswith(('Step', 'Summary')):
                # Add blank line before header if there isn't one
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')
                formatted_lines.append(header_text)
                continue

        # Handle empty lines
        if not line.strip():
            # Keep empty lines between paragraphs, but avoid duplicates
            if formatted_lines and formatted_lines[-1].strip():
                formatted_lines.append('')
            continue

        # Clean up markdown formatting, but preserve code backticks
        cleaned_line = line
        if '`' not in line:
            cleaned_line = line.replace('*', '').replace('_', '')

        # Add the line
        formatted_lines.append(cleaned_line.strip())

        # Add empty line after certain blocks
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Add empty line before headers
            if next_line.startswith(('#', 'Step', 'Summary')):
                formatted_lines.append('')
            # Add empty line after equations (lines with =)
            elif '=' in cleaned_line and not next_line.startswith(('This', 'Since', 'Therefore')):
                formatted_lines.append('')

    # Clean up trailing empty lines
    while formatted_lines and not formatted_lines[-1].strip():
        formatted_lines.pop()
    
    return '\n'.join(formatted_lines)


def format_solution(answer: str) -> str:
    if not answer:
        return "Sorry, I encountered an error. Please try again later."

    # Extract LaTeX blocks and format them
    text, latex_blocks = extract_latex_blocks(answer)

    # Replace each LaTeX block with its formatted version
    for i, latex in enumerate(latex_blocks):
        formatted_math = format_math_expression(latex)
        text = text.replace(f"__LATEX_{i}__", f"`{formatted_math}`")

    # Format the final text
    formatted_text = format_line_message(text)
    return formatted_text


async def generate_answer(user_input: str) -> str:
    """Generate an answer using OpenRouter and format math expressions"""
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
    
    # Format the final text
    formatted_text = format_solution(answer)
    
    end_time = dt.datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Answer generation took {duration:.2f} seconds.")
    
    return formatted_text
