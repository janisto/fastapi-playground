"""
Shared constants for the core module.
"""

API_V1_PREFIX = "/v1"

CONSUMER_DOCUMENTATION_PATHS = frozenset({"/.well-known/api-catalog", "/llms.txt", "/llms-full.txt"})
LLMS_INDEX_LINK = '</llms.txt>; rel="describedby"; type="text/plain"'
API_CATALOG_LINK = '</.well-known/api-catalog>; rel="api-catalog"; type="application/linkset+json"'
OPENAPI_DOCUMENT_LINK = '</openapi.json>; rel="service-desc"; type="application/json"'
