"""
Test isolation for Genkit process-wide integrations.
"""

import genkit._ai._aio as genkit_aio
import genkit.plugins.google_cloud as google_cloud


def _production_environment() -> bool:
    """
    Disable the development reflection server during unit tests.
    """
    return False


def _disable_gcp_telemetry(**_kwargs: object) -> None:
    """
    Prevent unit tests from exporting logs, metrics, or traces.
    """


genkit_aio.is_dev_environment = _production_environment
google_cloud.add_gcp_telemetry = _disable_gcp_telemetry
