# Deploy with `firebase deploy --only functions`

from firebase_admin import initialize_app
from firebase_functions import https_fn, options, params

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
options.set_global_options(
    region=options.SupportedRegion.EUROPE_WEST4,
    memory=options.MemoryOption.MB_128,
    min_instances=params.IntParam("MIN_INSTANCES", default=0),
    max_instances=params.IntParam("MAX_INSTANCES", default=2),
)

initialize_app()

# Only run this block for Vertex AI API. Needs GOOGLE_CLOUD_PROJECT env var set.
# See https://googleapis.github.io/python-genai/
# client = genai.Client(vertexai=True, project="your-project-id", location="europe-west4")


@https_fn.on_request()
def on_request_example(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response("Hello world!")
