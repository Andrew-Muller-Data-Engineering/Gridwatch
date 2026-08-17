"""
GridWatch — bridges Phase 3's curated Parquet data from AWS S3 into
BigQuery, since the two clouds don't share storage natively.

Unlike deploy_neso_ingest.py / deploy_stepfunctions.py / deploy_glue_transform.py,
this script doesn't create any AWS or GCP IAM role — there's no cloud-hosted
compute here for a role to belong to. It runs on your own machine, using
your own already-authenticated identities: your AWS IAM user's credentials
(from `aws configure`, Part 1.1) to read S3, and your Google Cloud
Application Default Credentials (from `gcloud auth application-default
login` — see the How section if you haven't run this yet) to write to
GCS and BigQuery.

Three steps, run in order, every time: download today's curated Parquet
partition from S3, re-upload it to GCS (BigQuery can only load from GCS,
not directly from S3), then load it into BigQuery from there. The
destination table is created automatically on first run — Parquet files
carry their own schema, so BigQuery reads it straight from the files
rather than needing a schema defined by hand.

Run from the repo root, in VS Code's integrated terminal (.venv
activated), any time after Phase 3's Glue job has produced today's
curated Parquet:

    python warehouse/load_curated_to_bigquery.py
"""

import datetime as dt
import json
import pathlib
import tempfile

import boto3
from google.cloud import bigquery, storage

INFRA_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = INFRA_DIR / "bigquery_load_config.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def list_todays_s3_keys(s3, bucket, curated_prefix):
    """Only today's reading_date=... partition — matching the daily
    pipeline cadence, the same "process just today's folder" approach
    deploy_glue_transform.py's job itself already uses one step upstream."""
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    prefix = f"{curated_prefix}reading_date={today}/"

    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def copy_s3_keys_to_gcs(s3, gcs_client, config, keys):
    """Downloads each S3 object to a local temp file, then re-uploads it
    to GCS at the equivalent path (curated_prefix swapped for gcs_prefix,
    everything after that kept identical) — so the GCS copy mirrors the
    S3 layout exactly, partition folder names included."""
    gcs_bucket = gcs_client.bucket(config["gcs_bucket"])
    s3_prefix = config["s3_curated_prefix"]
    gcs_uris = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for key in keys:
            local_path = pathlib.Path(tmp_dir) / pathlib.Path(key).name
            s3.download_file(config["s3_curated_bucket"], key, str(local_path))

            relative_path = key[len(s3_prefix):] if key.startswith(s3_prefix) else pathlib.Path(key).name
            gcs_key = f"{config['gcs_prefix']}{relative_path}"

            blob = gcs_bucket.blob(gcs_key)
            blob.upload_from_filename(str(local_path))
            gcs_uris.append(f"gs://{config['gcs_bucket']}/{gcs_key}")
            print(f"Copied s3://{config['s3_curated_bucket']}/{key} -> {gcs_uris[-1]}")

    return gcs_uris


def ensure_dataset(bq_client, project_id, dataset_id, location):
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    bq_client.create_dataset(dataset, exists_ok=True)
    return dataset_ref


def load_into_bigquery(bq_client, config, dataset_ref, gcs_uris):
    table_ref = dataset_ref.table(config["bigquery_table"])

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        # Appends each day's rows rather than overwriting — correct for a
        # growing time-series fact table. Re-running this script twice on
        # the same day will append that day's rows twice; a production
        # version would check for or de-duplicate an existing partition
        # first, deliberately left out here to keep this script's scope
        # matched to what the project actually needs.
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        # Physically partitions the BigQuery table by this column, so a
        # query filtered to one date only scans that date's data —
        # exactly the reason the curated Parquet itself was already
        # partitioned by reading_date in Phase 3.
        time_partitioning=bigquery.TimePartitioning(field=config["partition_field"]),
    )

    load_job = bq_client.load_table_from_uri(gcs_uris, table_ref, job_config=job_config)
    load_job.result()  # blocks until the load finishes (or raises on failure)

    table = bq_client.get_table(table_ref)
    print(
        f"Loaded {load_job.output_rows} row(s) into "
        f"{config['gcp_project_id']}.{config['bigquery_dataset']}.{config['bigquery_table']} "
        f"({table.num_rows} total rows in the table now)."
    )


def main():
    config = load_json(CONFIG_PATH)

    s3 = boto3.client("s3", region_name=config["aws_region"])
    gcs_client = storage.Client(project=config["gcp_project_id"])
    bq_client = bigquery.Client(project=config["gcp_project_id"])

    keys = list_todays_s3_keys(s3, config["s3_curated_bucket"], config["s3_curated_prefix"])
    if not keys:
        print("No curated Parquet found for today yet — run the Glue job (or wait for the daily pipeline) first.")
        return

    gcs_uris = copy_s3_keys_to_gcs(s3, gcs_client, config, keys)

    dataset_ref = ensure_dataset(
        bq_client, config["gcp_project_id"], config["bigquery_dataset"], config["bigquery_dataset_location"]
    )
    load_into_bigquery(bq_client, config, dataset_ref, gcs_uris)


if __name__ == "__main__":
    main()
