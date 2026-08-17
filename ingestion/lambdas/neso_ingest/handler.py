"""
GridWatch — NESO Carbon Intensity ingestion Lambda.

Calls the NESO (National Energy System Operator) Carbon Intensity API's
regional endpoint and writes the raw, unmodified JSON response to S3,
keyed by the date and time it was fetched. This is deliberately "dumb" —
no filtering, no reshaping — because this is the raw zone: exactly what
came back from the API, nothing more. Cleaning happens in Phase 3.

Uses only the Python standard library (urllib) plus boto3, which is
pre-installed in every AWS Lambda Python runtime. That means this file can
be pasted directly into the Lambda console's inline code editor and
deployed with no zip file, no extra dependencies, and no packaging step —
the simplest possible path for a first Lambda. (requests would need to be
packaged in separately, since it isn't part of the standard library or
pre-installed in the Lambda runtime.)
"""

import json
import urllib.request
from datetime import datetime, timezone

import boto3

# Replace with your actual bucket name (S3 bucket names are globally
# unique, so "gridwatch-raw" alone is very unlikely to be free).
S3_BUCKET = "gridwatch-raw-andy817"

NESO_API_URL = "https://api.carbonintensity.org.uk/regional"

s3 = boto3.client("s3")


def lambda_handler(event, context):
    with urllib.request.urlopen(NESO_API_URL, timeout=10) as response:
        raw_bytes = response.read()

    # Validate it's actually JSON before we bother writing it to S3 — if
    # the API is down or returns something unexpected, better to fail
    # loudly here (Step Functions will retry) than to silently store junk.
    json.loads(raw_bytes)

    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    key = f"raw/neso-demand/{date_prefix}/{timestamp}.json"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=raw_bytes,
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "bucket": S3_BUCKET,
        "key": key,
    }
