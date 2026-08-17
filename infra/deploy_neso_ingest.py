"""
Deploys the NESO ingest Lambda straight from this repo — no AWS Console
copy-paste required.

Safe to re-run any time you edit handler.py: it creates the IAM role and
the Lambda function on the very first run, and on every run after that it
just pushes the updated code (and config) to the existing function. The
repo is the source of truth; the AWS Console becomes a place to look at
logs and test results, not a place to edit code.

Run from the repo root, in VS Code's integrated terminal (with your .venv
activated, same as every other command in the build guide):

    python infra/deploy_neso_ingest.py
"""

import io
import json
import pathlib
import time
import zipfile

import boto3

# infra/ is one level below the repo root, so the handler path in the
# config (e.g. "ingestion/lambdas/neso_ingest/handler.py") is relative to
# the parent of this file's folder.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_PATH = pathlib.Path(__file__).resolve().parent / "neso_ingest_lambda_config.json"
TRUST_POLICY_PATH = pathlib.Path(__file__).resolve().parent / "neso_ingest_trust_policy.json"

# AWS-managed policy (maintained by AWS, not by you) that grants just
# enough CloudWatch Logs access for a Lambda to write its own logs. Every
# Lambda needs at least this.
BASIC_EXECUTION_POLICY_ARN = (
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def build_s3_write_policy(bucket_name):
    """The same inline policy the build guide originally had you paste
    into the console by hand in Step 6 — now generated from the bucket
    name in the config file instead, so there's only one place to update
    it."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            }
        ],
    }


def ensure_role(iam, config):
    """Creates the Lambda's execution role if it doesn't exist yet, and
    makes sure its permissions are up to date either way. Returns the
    role's ARN, which the Lambda function needs to be created/updated."""
    role_name = config["role_name"]
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"IAM role '{role_name}' already exists — reusing it.")
        role_is_new = False
    except iam.exceptions.NoSuchEntityException:
        with open(TRUST_POLICY_PATH) as f:
            trust_policy = json.load(f)
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for the {config['function_name']} Lambda",
        )["Role"]
        print(f"Created IAM role '{role_name}'.")
        role_is_new = True

    iam.attach_role_policy(RoleName=role_name, PolicyArn=BASIC_EXECUTION_POLICY_ARN)
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{config['function_name']}-s3-write",
        PolicyDocument=json.dumps(build_s3_write_policy(config["s3_bucket"])),
    )
    print(f"Attached CloudWatch Logs + S3 write permissions to '{role_name}'.")

    if role_is_new:
        # IAM is "eventually consistent" — a brand-new role can fail
        # Lambda's create_function call if used within the first few
        # seconds, before it's finished propagating. This wait is a
        # pragmatic fix for that, not a bug.
        print("Waiting 10s for the new role to finish propagating...")
        time.sleep(10)

    return role["Arn"]


def zip_handler(config):
    """Zips just handler.py in memory — no third-party dependencies to
    bundle (see the build guide's Why section on urllib vs requests)."""
    handler_path = REPO_ROOT / config["handler_file"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(handler_path, arcname=handler_path.name)
    return buffer.getvalue()


def deploy_function(lambda_client, config, role_arn, zip_bytes):
    function_name = config["function_name"]
    try:
        lambda_client.get_function(FunctionName=function_name)
        exists = True
    except lambda_client.exceptions.ResourceNotFoundException:
        exists = False

    if not exists:
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime=config["runtime"],
            Role=role_arn,
            Handler=config["handler"],
            Code={"ZipFile": zip_bytes},
            Timeout=config["timeout"],
            MemorySize=config["memory_size"],
            Description=config["description"],
        )
        print(f"Created new Lambda function '{function_name}'.")
        return

    lambda_client.update_function_code(FunctionName=function_name, ZipFile=zip_bytes)
    # Lambda won't accept a config update while a code update is still
    # being applied, so wait for it to finish first.
    lambda_client.get_waiter("function_updated").wait(FunctionName=function_name)
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Runtime=config["runtime"],
        Role=role_arn,
        Handler=config["handler"],
        Timeout=config["timeout"],
        MemorySize=config["memory_size"],
        Description=config["description"],
    )
    print(f"Updated code and config for existing function '{function_name}'.")


def main():
    config = load_config()
    session = boto3.Session(region_name=config["region"])
    iam = session.client("iam")
    lambda_client = session.client("lambda")

    role_arn = ensure_role(iam, config)
    zip_bytes = zip_handler(config)
    deploy_function(lambda_client, config, role_arn, zip_bytes)

    print(
        "Done. Check the function in the Lambda console, or run the Test "
        "step from the build guide, to confirm it works."
    )


if __name__ == "__main__":
    main()
