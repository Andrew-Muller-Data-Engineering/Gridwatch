"""
GridWatch — BigQuery-load Lambda.

The automated version of warehouse/load_curated_to_bigquery.py (the
script you run yourself from your laptop) — same three steps: copy
today's curated Parquet partition from S3 to GCS, then load it into
BigQuery. Runs as the third step in the daily Step Functions workflow,
straight after the Glue transform job finishes.

Authenticates to GCP using a service account key stored in AWS Secrets
Manager, fetched fresh on every invocation and held only in memory —
never written to disk — since this Lambda has no laptop, no browser, and
no "you" to run `gcloud auth login` as.
"""

import datetime as dt
import json
import os

import boto3
from google.cloud import bigquery, storage
from google.oauth2 import service_account

GCP_SECRET_ARN = os.environ["GCP_SECRET_ARN"]
GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
GCS_BUCKET = os.environ["GCS_BUCKET"]
GCS_PREFIX = os.environ["GCS_PREFIX"]
S3_CURATED_BUCKET = os.environ["S3_CURATED_BUCKET"]
S3_CURATED_PREFIX = os.environ["S3_CURATED_PREFIX"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_DATASET_LOCATION = os.environ["BQ_DATASET_LOCATION"]
BQ_TABLE = os.environ["BQ_TABLE"]
PARTITION_FIELD = os.environ["PARTITION_FIELD"]


def get_gcp_credentials(secrets_client):
    secret_value = secrets_client.get_secret_value(SecretId=GCP_SECRET_ARN)["SecretString"]
    info = json.loads(secret_value)
    return service_account.Credentials.from_service_account_info(info)


def list_todays_s3_keys(s3):
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    prefix = f"{S3_CURATED_PREFIX}reading_date={today}/"
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_CURATED_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def copy_s3_keys_to_gcs(s3, gcs_client, keys):
    """Same download-then-reupload approach as the local script's
    copy_s3_keys_to_gcs() — downloads to Lambda's writable /tmp (cleared
    between cold starts, reused-but-overwritten on warm ones) rather than
    holding file contents in memory, then removes each file immediately
    after upload so a long-running or reused execution environment never
    accumulates leftover files across invocations."""
    gcs_bucket = gcs_client.bucket(GCS_BUCKET)
    gcs_uris = []

    for key in keys:
        local_path = f"/tmp/{key.split('/')[-1]}"
        s3.download_file(S3_CURATED_BUCKET, key, local_path)

        relative_path = key[len(S3_CURATED_PREFIX):] if key.startswith(S3_CURATED_PREFIX) else key.split("/")[-1]
        gcs_key = f"{GCS_PREFIX}{relative_path}"

        blob = gcs_bucket.blob(gcs_key)
        blob.upload_from_filename(local_path)
        gcs_uris.append(f"gs://{GCS_BUCKET}/{gcs_key}")
        os.remove(local_path)
        print(f"Copied s3://{S3_CURATED_BUCKET}/{key} -> {gcs_uris[-1]}")

    return gcs_uris


def ensure_dataset(bq_client):
    dataset_ref = bigquery.DatasetReference(GCP_PROJECT_ID, BQ_DATASET)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = BQ_DATASET_LOCATION
    bq_client.create_dataset(dataset, exists_ok=True)
    return dataset_ref


def load_into_bigquery(bq_client, dataset_ref, gcs_uris):
    table_ref = dataset_ref.table(BQ_TABLE)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(field=PARTITION_FIELD),
    )
    load_job = bq_client.load_table_from_uri(gcs_uris, table_ref, job_config=job_config)
    load_job.result()
    return load_job.output_rows


def lambda_handler(event, context):
    secrets_client = boto3.client("secretsmanager")
    credentials = get_gcp_credentials(secrets_client)

    s3 = boto3.client("s3")
    gcs_client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
    bq_client = bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)

    keys = list_todays_s3_keys(s3)
    if not keys:
        print("No curated Parquet found for today yet.")
        return {"statusCode": 200, "rows_loaded": 0, "files_processed": 0}

    gcs_uris = copy_s3_keys_to_gcs(s3, gcs_client, keys)
    dataset_ref = ensure_dataset(bq_client)
    rows_loaded = load_into_bigquery(bq_client, dataset_ref, gcs_uris)

    print(f"Loaded {rows_loaded} row(s) from {len(keys)} file(s).")
    return {"statusCode": 200, "rows_loaded": rows_loaded, "files_processed": len(keys)}
