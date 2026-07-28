"""
Hello request models.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import Name

# Supported language codes for greetings
SupportedLanguage = Literal["en", "fi", "es", "fr", "de"]

GREETINGS: dict[SupportedLanguage, str] = {
    "en": "Hello",
    "fi": "Hei",
    "es": "Hola",
    "fr": "Bonjour",
    "de": "Hallo",
}


class GreetingRequest(BaseModel):
    """
    Request model for generating a personalized greeting.
    """

    model_config = ConfigDict(extra="forbid")

    name: Name = Field(
        ...,
        description="Name for personalized greeting",
        examples=["Alice"],
    )
    language: SupportedLanguage = Field(
        default="en",
        description="Language code for greeting (en, fi, es, fr, de)",
        examples=["en", "fi", "es"],
    )
