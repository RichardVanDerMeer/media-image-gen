"""Keyword extraction using regular Gemini model."""

import os
from typing import List, Optional
from google import genai
from google.genai import types


def extract_keywords(book_title: str, api_key: Optional[str] = None) -> List[str]:
    """
    Extract keywords related to a book title using Gemini API.

    Args:
        book_title: The title of the book
        api_key: Gemini API key (if None, uses GEMINI_API_KEY from environment)

    Returns:
        List of keyword strings extracted from the book title

    Raises:
        ValueError: If API key is not provided and not in environment
        Exception: If API call fails
    """
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment or provided as argument"
        )

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You are an AI agent that responds with a list of words / topics that are "
        "related to a given book title, the responses will help another AI Agent "
        "generate an image of the setting / atmosphere of that specific book"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=book_title)],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=[types.Part.from_text(text=system_instruction)],
            ),
        )

        # Extract text from response
        if response.text:
            keywords_text = response.text.strip()
            # Parse keywords: split by newlines, filter empty lines, strip whitespace
            keywords = [
                keyword.strip()
                for keyword in keywords_text.split("\n")
                if keyword.strip()
            ]
            return keywords
        else:
            return []

    except Exception as e:
        # Log error but don't raise - caller should handle gracefully
        print(f"Warning: Keyword extraction failed: {e}")
        return []
