import json
import logging
import random
from enum import StrEnum

from firebase_admin import initialize_app
from firebase_functions import https_fn, options, params
from genkit.ai import Genkit, Output
from genkit.aio.loop import create_loop, run_async
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.google_genai import VertexAI
from genkit.types import GenkitError
from pydantic import BaseModel, Field

options.set_global_options(
    region=options.SupportedRegion.EUROPE_WEST4,
    memory=options.MemoryOption.MB_512,
    timeout_sec=params.IntParam("TIMEOUT_SEC", default=120),
    min_instances=params.IntParam("MIN_INSTANCES", default=0),
    max_instances=params.IntParam("MAX_INSTANCES", default=2),
)

# Initialize Firebase Admin SDK (credentials auto-detected on GCP)
initialize_app()

# Export Genkit telemetry to Cloud Trace and Cloud Monitoring (GCP only, not local dev)
add_gcp_telemetry(force_dev_export=False)

ai = Genkit(
    plugins=[VertexAI(location="europe-west4")],
    model="vertexai/gemini-2.5-flash",
)

# Create a persistent event loop for async operations
# This avoids the "Event loop is closed" error on warm starts
_loop = create_loop()

logger = logging.getLogger(__name__)


class JokeTopic(StrEnum):
    """
    Available dad joke topics.
    """

    WORK = "work"
    TECH = "tech"
    FOOD = "food"
    RELATIONSHIPS = "relationships"


class JokeStyle(StrEnum):
    """
    Dad joke styles/techniques.
    """

    PUN = "pun"
    LITERAL = "literal"
    HOMOPHONE = "homophone"
    ANTICLIMAX = "anticlimax"
    MISUNDERSTANDING = "misunderstanding"


class GeneratedJoke(BaseModel):
    """
    LLM output schema (strictly enforced by Genkit).

    The model MUST return JSON matching this exact structure.
    """

    setup: str = Field(description="The question or setup line")
    punchline: str = Field(description="The punchline or answer")


class DadJoke(BaseModel):
    """
    API response schema - final output to the client.
    """

    setup: str = Field(description="The question or setup line", examples=["Why don't eggs tell jokes?"])
    punchline: str = Field(description="The punchline or answer", examples=["They'd crack each other up!"])
    topic: JokeTopic | None = Field(
        default=None,
        description="The topic of the joke, if specified",
        examples=["food"],
    )
    style: JokeStyle = Field(description="The joke style used", examples=["pun"])


# Style definitions - single source of truth for prompt generation
STYLE_DEFINITIONS: dict[JokeStyle, str] = {
    JokeStyle.PUN: "Classic wordplay or double meaning",
    JokeStyle.LITERAL: "Taking something literally that shouldn't be",
    JokeStyle.HOMOPHONE: "Words that sound alike but mean different things",
    JokeStyle.ANTICLIMAX: "Building up to a disappointing pun",
    JokeStyle.MISUNDERSTANDING: "Pretending to misunderstand on purpose",
}


def build_system_prompt(style: JokeStyle) -> str:
    """
    Build system prompt for a specific joke style.
    """
    style_desc = STYLE_DEFINITIONS[style]
    return f"""You are a dad joke generator. Generate family-friendly jokes that elicit eye-rolls and groans.

Use this style: {style.value} - {style_desc}"""


@ai.flow()
async def generate_dad_joke(topic: JokeTopic | None = None) -> DadJoke:
    """
    Generate a dad joke using Gemini.

    Input: Optional topic constraint (text prompt)
    Output: Strictly validated GeneratedJoke schema
    """
    style = random.choice(list(JokeStyle))  # noqa: S311
    user_prompt = f"Generate a dad joke about {topic.value}." if topic else "Generate a dad joke."

    result = await ai.generate(
        system=build_system_prompt(style),
        prompt=user_prompt,
        output=Output(schema=GeneratedJoke),
        config={
            "temperature": 0.8,
            "thinking_config": {
                "thinking_budget": 4096,
            },
        },
    )
    generated = result.output
    return DadJoke(
        setup=generated.setup,
        punchline=generated.punchline,
        topic=topic,
        style=style,
    )


@https_fn.on_request()
def dad_joke(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint that returns a dad joke.

    Query params:
        topic: Optional topic (work, tech, food, relationships)

    Returns:
        JSON with setup, punchline, topic, and style fields.
    """
    try:
        topic_param = req.args.get("topic")
        topic = JokeTopic(topic_param.lower()) if topic_param else None

        joke = run_async(_loop, lambda: generate_dad_joke(topic))

        logger.info(
            "Generated dad joke",
            extra={
                "topic": topic,
                "style": joke.style,
                "setup": joke.setup,
                "punchline": joke.punchline,
            },
        )

        return https_fn.Response(
            joke.model_dump_json(),
            content_type="application/json",
        )

    except ValueError:
        valid_topics = [t.value for t in JokeTopic]
        return https_fn.Response(
            json.dumps(
                {
                    "error": "INVALID_ARGUMENT",
                    "message": f"Invalid topic. Valid: {valid_topics}",
                }
            ),
            status=400,
            content_type="application/json",
        )

    except GenkitError as e:
        logger.exception(
            "Genkit error generating joke",
            extra={"genkit_status": e.status, "genkit_message": str(e)},
        )
        return https_fn.Response(
            json.dumps({"error": e.status, "message": "Failed to generate joke"}),
            status=503,
            content_type="application/json",
        )

    except Exception:
        logger.exception("Unexpected error generating joke")
        return https_fn.Response(
            json.dumps({"error": "INTERNAL", "message": "An unexpected error occurred"}),
            status=500,
            content_type="application/json",
        )
