"""
Deploys the BigQuery-load Lambda straight from the repo — the same
config+trust-policy+deploy-script pattern as every other resource in
this project, extended to cover the automated version of Phase 4's
cross-cloud bridge. ingestion/lambdas/neso_bigquery_load/handler.py is a
Lambda-compatible port of warehouse/load_curated_to_bigquery.py, the
script you run yourself.

One genuine difference from deploy_neso_ingest.py: that Lambda only uses
boto3 and the Python standard library, both already built into every
Lambda runtime, so zipping handler.py alone was enough. This Lambda also
needs google-cloud-storage and google-cloud-bigquery, which aren't part
of any Lambda runtime. So this script does two things
deploy_neso_ingest.py didn't need to:

1. pip-installs those packages into a build folder, targeting Lambda's
   own Linux platform explicitly (--platform manylinux2014_x86_64) —
   without this, pip installs packages built for whatever OS you're
   running this script on, which fail to import once uploaded to Lambda.
2. Checks the resulting zip's size. Lambda's API only accepts an inline
   ZipFile up to 50MB compressed — google-cloud-bigquery and its
   dependencies (grpc, protobuf, and so on) can realistically get close
   to or past that. If the zip is too big, this script uploads it to S3
   first and points Lambda at that instead (Lambda accepts a much larger
   package — up to 250MB unzipped — when it's loaded from S3 rather than
   uploaded inline).

Prerequisite — a manual, one-time setup this script deliberately does
NOT automate: a GCP service account must already exist, with a key
stored in AWS Secrets Manager under the name in
neso_bigquery_load_lambda_config.json's "gcp_secret_name". See the build
guide's Phase 4 "How" for those steps — a service account key is
sensitive enough to want doing deliberately by hand, not folded into a
script you might re-run without thinking about what it just did.

Run from the repo root, in VS Code's integrated terminal (.venv
activated), after that secret exists and deploy_glue_transform.py has
already been run at least once:

    python infra/deploy_bigquery_load_lambda.py
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import boto3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INFRA_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = INFRA_DIR / "neso_bigquery_load_lambda_config.json"
TRUST_POLICY_PATH = INFRA_DIR / "neso_bigquery_load_trust_policy.json"

# Lambda's direct inline-upload limit is 50MB compressed; leaving a
# safety margin below that rather than cutting it exactly at 50MB.
INLINE_ZIP_SIZE_LIMIT_BYTES = 45_000_000


def load_json(path):
    with open(path) as f:
        return json.load(f)


def build_permissions_policy(config, secret_arn):
    bucket_arn = f"arn:aws:s3:::{config['s3_curated_bucket']}"
    object_arn = f"{bucket_arn}/{config['s3_curated_prefix']}*"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                # s3:ListBucket is a bucket-level action — it needs the
                # bucket's own ARN (no path), not the object-level ARN
                # below, even though this Lambda only ever lists within
                # one prefix. The s3:prefix condition is what actually
                # keeps it scoped to just that prefix, rather than
                # letting it list the whole bucket.
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": bucket_arn,
                "Condition": {
                    "StringLike": {"s3:prefix": [f"{config['s3_curated_prefix']}*"]}
                },
            },
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": object_arn,
            },
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": secret_arn,
            },
        ],
    }


def ensure_role(iam, config, secret_arn):
    role_name = config["role_name"]
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"IAM role '{role_name}' already exists — reusing it.")
        role_is_new = False
    except iam.exceptions.NoSuchEntityException:
        trust_policy = load_json(TRUST_POLICY_PATH)
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for the {config['function_name']} Lambda",
        )["Role"]
        print(f"Created IAM role '{role_name}'.")
        role_is_new = True

    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{config['function_name']}-s3-and-secret-access",
        PolicyDocument=json.dumps(build_permissions_policy(config, secret_arn)),
    )
    print(f"Attached permissions to '{role_name}' (S3 read on the curated prefix, Secrets Manager read on one secret).")

    if role_is_new:
        print("Waiting 10s for the new role to finish propagating...")
        time.sleep(10)

    return role["Arn"]


def build_deployment_zip(config):
    handler_dir = REPO_ROOT / config["handler_dir"]
    requirements_file = REPO_ROOT / config["requirements_file"]

    build_dir = tempfile.mkdtemp()
    print("Installing dependencies for Lambda's Linux environment (this can take a minute)...")
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "-r", str(requirements_file),
            "--target", build_dir,
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.13",
            "--only-binary=:all:",
        ],
        check=True,
    )

    for item in handler_dir.iterdir():
        if item.name == "requirements.txt":
            continue
        dest = pathlib.Path(build_dir) / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    zip_path = pathlib.Path(tempfile.mkdtemp()) / "deployment.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in pathlib.Path(build_dir).rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(build_dir))

    size_mb = zip_path.stat().st_size / 1_000_000
    print(f"Built deployment package: {size_mb:.1f}MB")
    return zip_path


def resolve_code_source(s3, config, zip_path):
    """Returns the `Code=` kwargs for create_function/the equivalent for
    update_function_code — inline bytes if the zip is small enough,
    otherwise uploaded to S3 first with Lambda pointed at that instead."""
    zip_size = zip_path.stat().st_size

    if zip_size <= INLINE_ZIP_SIZE_LIMIT_BYTES:
        return {"ZipFile": zip_path.read_bytes()}

    print(
        f"Deployment package ({zip_size / 1_000_000:.1f}MB) is too large for a direct upload — "
        f"uploading to s3://{config['deployment_bucket']}/{config['deployment_key']} instead."
    )
    s3.upload_file(str(zip_path), config["deployment_bucket"], config["deployment_key"])
    return {"S3Bucket": config["deployment_bucket"], "S3Key": config["deployment_key"]}


def deploy_function(lambda_client, s3, config, role_arn, zip_path, secret_arn):
    name = config["function_name"]
    env_vars = {
        "GCP_SECRET_ARN": secret_arn,
        "GCP_PROJECT_ID": config["gcp_project_id"],
        "GCS_BUCKET": config["gcs_bucket"],
        "GCS_PREFIX": config["gcs_prefix"],
        "S3_CURATED_BUCKET": config["s3_curated_bucket"],
        "S3_CURATED_PREFIX": config["s3_curated_prefix"],
        "BQ_DATASET": config["bigquery_dataset"],
        "BQ_DATASET_LOCATION": config["bigquery_dataset_location"],
        "BQ_TABLE": config["bigquery_table"],
        "PARTITION_FIELD": config["partition_field"],
    }
    code_source = resolve_code_source(s3, config, zip_path)

    try:
        lambda_client.get_function(FunctionName=name)
        exists = True
    except lambda_client.exceptions.ResourceNotFoundException:
        exists = False

    if not exists:
        lambda_client.create_function(
            FunctionName=name,
            Runtime=config["runtime"],
            Role=role_arn,
            Handler=config["handler"],
            Code=code_source,
            Timeout=config["timeout"],
            MemorySize=config["memory_size"],
            Environment={"Variables": env_vars},
        )
        print(f"Created new Lambda function '{name}'.")
        return

    if "ZipFile" in code_source:
        lambda_client.update_function_code(FunctionName=name, ZipFile=code_source["ZipFile"])
    else:
        lambda_client.update_function_code(
            FunctionName=name, S3Bucket=code_source["S3Bucket"], S3Key=code_source["S3Key"]
        )

    # Code updates must finish propagating before a configuration update
    # can be applied — the Lambda-specific variant of the IAM
    # eventual-consistency issue from Phase 2.
    waiter = lambda_client.get_waiter("function_updated")
    waiter.wait(FunctionName=name)

    lambda_client.update_function_configuration(
        FunctionName=name,
        Role=role_arn,
        Handler=config["handler"],
        Timeout=config["timeout"],
        MemorySize=config["memory_size"],
        Environment={"Variables": env_vars},
    )
    print(f"Updated existing Lambda function '{name}'.")


def main():
    config = load_json(CONFIG_PATH)
    session = boto3.Session(region_name=config["region"])
    iam = session.client("iam")
    s3 = session.client("s3")
    lambda_client = session.client("lambda")
    secrets_client = session.client("secretsmanager")

    secret_arn = secrets_client.describe_secret(SecretId=config["gcp_secret_name"])["ARN"]

    role_arn = ensure_role(iam, config, secret_arn)
    zip_path = build_deployment_zip(config)
    deploy_function(lambda_client, s3, config, role_arn, zip_path, secret_arn)

    print("Done. Test it from the Lambda console before wiring it into the Step Functions workflow.")


if __name__ == "__main__":
    main()
