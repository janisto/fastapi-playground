import asyncio
import json
import os
import random
import threading
from collections.abc import Callable, Coroutine
from enum import StrEnum
from typing import cast

import structlog
from firebase_admin import initialize_app
from firebase_functions import https_fn, logger, options, params
from genkit import Genkit, GenkitError
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.google_genai import VertexAI
from pydantic import BaseModel, Field

# Configure structlog for JSON output in Cloud Run/Functions (Genkit uses structlog internally)
# This ensures Genkit's logs appear as structured jsonPayload in Cloud Logging
if os.getenv("K_SERVICE"):  # Running in Cloud Run/Functions
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )

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
    model="vertexai/gemini-3-pro-preview",
)

_loop = asyncio.new_event_loop()


def _run_event_loop() -> None:
    """
    Run the shared async event loop for warm function instances.
    """
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


_loop_thread = threading.Thread(target=_run_event_loop, daemon=True)
_loop_thread.start()


def run_async[T](coro: Coroutine[object, object, T]) -> T:
    """
    Run a coroutine on the shared event loop from a sync Firebase handler.
    """
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result()


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
        output_schema=GeneratedJoke,
        config={
            "thinking_config": {
                "thinking_level": "MEDIUM",
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

        joke_flow = cast("Callable[[JokeTopic | None], Coroutine[object, object, DadJoke]]", generate_dad_joke)
        joke = run_async(joke_flow(topic))

        logger.info(
            "Generated dad joke",
            topic=topic.value if topic else None,
            style=joke.style.value,
        )

        return https_fn.Response(
            joke.model_dump_json(),
            content_type="application/json",
        )

    except ValueError:
        valid_topics = [t.value for t in JokeTopic]
        logger.warn("Invalid topic requested", topic=topic_param, valid_topics=valid_topics)
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
        logger.error(
            "Genkit error generating joke",
            error=e,
            genkit_status=e.status,
            genkit_message=str(e),
        )
        return https_fn.Response(
            json.dumps({"error": e.status, "message": "Failed to generate joke"}),
            status=503,
            content_type="application/json",
        )

    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error generating joke", error=e)
        return https_fn.Response(
            json.dumps({"error": "INTERNAL", "message": "An unexpected error occurred"}),
            status=500,
            content_type="application/json",
        )
