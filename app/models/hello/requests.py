"""Hello request model."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import BoundedName


class HelloCreate(BaseModel):
    """Closed personalized greeting request."""

    name: BoundedName = Field(description="Name used verbatim in the greeting", examples=["Ada"])
    model_config = ConfigDict(extra="forbid", strict=True)
