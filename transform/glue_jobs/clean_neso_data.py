"""
GridWatch — Glue Python Shell transform job.

Reads the raw NESO Carbon Intensity JSON that the ingestion Lambda wrote
for today, drops the four GB/England/Scotland/Wales aggregate entries
that don't map onto Phase 1's 14 real DNO regions, flattens each region's
generation mix into fixed columns, casts everything to proper types, and
writes the result out as Hive-style partitioned Parquet (partitioned by
reading_date) into the curated S3 zone — the shape a Glue Crawler, Athena,
or a BigQuery external table all expect for partition discovery.

Run as a Glue Python Shell job (not Spark) — deployed and scheduled via
infra/deploy_glue_transform.py and infra/deploy_stepfunctions.py, never
run directly. `raw_bucket` / `raw_prefix` / `curated_bucket` /
`curated_prefix` arrive as job parameters (see
infra/neso_transform_glue_config.json), not hardcoded here, so changing a
bucket or prefix never requires touching this file.
"""

import datetime as dt
import json
import pathlib
import sys
import tempfile

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from awsglue.utils import getResolvedOptions

# regionid 1-14 are the real DNO regions, matching Phase 1's region_id.
# regionid 15-18 are England/Scotland/Wales/GB aggregates — present in
# every raw file, but with no matching row in Phase 1's accounts table,
# so they're not useful for the Phase 5 join. Keeping them in the raw
# zone (Phase 2's job) but dropping them here (Phase 3's job) is the
# raw-vs-curated split described in the build guide's Phase 2 Why.
REAL_DNO_REGION_IDS = set(range(1, 15))

FUEL_TYPES = ["biomass", "coal", "imports", "gas", "nuclear", "other", "hydro", "solar", "wind"]


def list_raw_keys(s3, bucket, prefix):
    """Every object under today's date folder — usually just one file, but
    written to handle more than one gracefully (e.g. a re-run, or a future
    switch to a more frequent ingestion cadence)."""
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def parse_object(raw_bytes, source_key):
    """Turns one raw JSON file into a list of flat row dicts — one row per
    real DNO region. Returns an empty list (with a printed warning,
    rather than raising) for anything malformed, so one bad file doesn't
    fail the whole day's job — the "handle missing or malformed readings"
    requirement from the build guide's Phase 3 plan."""
    try:
        payload = json.loads(raw_bytes)
    except json.JSONDecodeError as e:
        print(f"Skipping {source_key}: not valid JSON ({e})")
        return []

    rows = []
    for entry in payload.get("data", []):
        period_from = entry.get("from")
        period_to = entry.get("to")
        for region in entry.get("regions", []):
            region_id = region.get("regionid")
            if region_id not in REAL_DNO_REGION_IDS:
                continue

            intensity = region.get("intensity", {})
            row = {
                "region_id": region_id,
                "dno_region": region.get("dnoregion"),
                "region_name": region.get("shortname"),
                "period_from": period_from,
                "period_to": period_to,
                "carbon_intensity_forecast": intensity.get("forecast"),
                "carbon_intensity_index": intensity.get("index"),
                "source_key": source_key,
            }
            # generationmix arrives as a list of {"fuel": ..., "perc": ...}
            # pairs — flattened here into one column per fuel type, rather
            # than kept as a nested list, since a flat row-per-region
            # table is what the Phase 5 SQL (joins, window functions) and
            # a BigQuery external table both expect.
            mix_by_fuel = {m.get("fuel"): m.get("perc") for m in region.get("generationmix", [])}
            for fuel in FUEL_TYPES:
                row[f"{fuel}_pct"] = mix_by_fuel.get(fuel)

            rows.append(row)
    return rows


def build_dataframe(rows):
    df = pd.DataFrame(rows)

    # Cast explicitly rather than trusting whatever pandas guessed from
    # the raw values — a single malformed or missing reading becomes a
    # proper null (NaN/NaT) in its column instead of silently turning the
    # whole column into a generic "object" dtype.
    df["region_id"] = df["region_id"].astype("Int64")
    df["carbon_intensity_forecast"] = pd.to_numeric(df["carbon_intensity_forecast"], errors="coerce")
    df["period_from"] = pd.to_datetime(df["period_from"], utc=True, errors="coerce")
    df["period_to"] = pd.to_datetime(df["period_to"], utc=True, errors="coerce")
    for fuel in FUEL_TYPES:
        df[f"{fuel}_pct"] = pd.to_numeric(df[f"{fuel}_pct"], errors="coerce")

    # The partition column: one calendar date per row, taken from the
    # settlement period's start. This is what "partitioned by date" means
    # in practice — a later query for one day can skip straight to that
    # partition's files instead of scanning the whole curated zone.
    df["reading_date"] = df["period_from"].dt.date.astype(str)

    return df


def write_partitioned_parquet(df, bucket, prefix):
    """Writes Hive-style partitioned Parquet (reading_date=YYYY-MM-DD/...)
    to a local temp folder via pyarrow, then uploads each resulting file
    to S3 preserving that same folder structure. Avoids needing s3fs (an
    extra dependency) just to let pandas/pyarrow write to an s3:// path
    directly — boto3, already built into every Glue Python Shell job,
    does the upload instead."""
    table = pa.Table.from_pandas(df, preserve_index=False)
    s3 = boto3.client("s3")

    with tempfile.TemporaryDirectory() as tmp_dir:
        pq.write_to_dataset(table, root_path=tmp_dir, partition_cols=["reading_date"])

        tmp_path = pathlib.Path(tmp_dir)
        uploaded = 0
        for local_file in tmp_path.rglob("*.parquet"):
            relative_path = local_file.relative_to(tmp_path).as_posix()
            s3_key = f"{prefix}{relative_path}"
            s3.upload_file(str(local_file), bucket, s3_key)
            uploaded += 1

        print(f"Wrote {len(df)} row(s) across {uploaded} partition file(s) to s3://{bucket}/{prefix}")


def main():
    args = getResolvedOptions(sys.argv, ["raw_bucket", "raw_prefix", "curated_bucket", "curated_prefix"])
    s3 = boto3.client("s3")

    # Processes today's date folder — matching the ingestion Lambda's own
    # date-based key layout (raw/neso-demand/<date>/<timestamp>.json) —
    # since Step Functions runs this job right after that day's ingestion.
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    prefix = f"{args['raw_prefix']}{today}/"

    keys = list_raw_keys(s3, args["raw_bucket"], prefix)
    if not keys:
        print(f"No raw objects found under s3://{args['raw_bucket']}/{prefix} — nothing to transform today.")
        return

    rows = []
    for key in keys:
        body = s3.get_object(Bucket=args["raw_bucket"], Key=key)["Body"].read()
        rows.extend(parse_object(body, key))

    if not rows:
        print("No valid region readings found in today's raw files — nothing written.")
        return

    df = build_dataframe(rows)
    write_partitioned_parquet(df, args["curated_bucket"], args["curated_prefix"])


if __name__ == "__main__":
    main()
