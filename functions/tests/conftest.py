"""
Test isolation for Genkit process-wide integrations.
"""

import os

import genkit._ai._aio as genkit_aio

os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-test"


def _production_environment() -> bool:
    """
    Disable the development reflection server during unit tests.
    """
    return False


genkit_aio.is_dev_environment = _production_environment
