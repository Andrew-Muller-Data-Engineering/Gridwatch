"""
Deploys the Glue transform job straight from the repo — the same
boto3-deploy pattern used for the Lambda (deploy_neso_ingest.py) and the
Step Functions state machine + EventBridge schedule (deploy_stepfunctions.py),
extended to cover Phase 3.

One difference from the earlier two scripts: a Glue job doesn't run code
directly from your repo the way a Lambda does — Glue reads its script from
an S3 location. So this script has one extra job the earlier ones didn't:
uploading transform/glue_jobs/clean_neso_data.py to S3 before pointing the
Glue job at it.

Safe to re-run: creates everything fresh the first time (role, uploaded
script, job), updates everything in place on every run after that.

Run from the repo root, in VS Code's integrated terminal (.venv
activated):

    python infra/deploy_glue_transform.py
"""

import json
import pathlib
import time

import boto3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INFRA_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = INFRA_DIR / "neso_transform_glue_config.json"
TRUST_POLICY_PATH = INFRA_DIR / "neso_transform_trust_policy.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def build_s3_policy(config):
    """Three separate permissions, each scoped as narrowly as possible:
    read the raw zone (input), write the curated zone (output), and read
    the job's own script location (Glue needs to fetch its code from S3
    before it can run it — without this, the job fails before your
    transform logic ever executes)."""
    raw_arn = f"arn:aws:s3:::{config['raw_s3_bucket']}/{config['raw_s3_prefix']}*"
    curated_arn = f"arn:aws:s3:::{config['curated_s3_bucket']}/{config['curated_s3_prefix']}*"
    script_arn = f"arn:aws:s3:::{config['script_s3_bucket']}/{config['script_s3_key']}"

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": [raw_arn, script_arn],
            },
            {
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": curated_arn,
            },
        ],
    }


def ensure_role(iam, config):
    """Creates the Glue job's execution role if it doesn't exist yet, and
    (re)applies its permissions either way — same shape as the equivalent
    function in deploy_neso_ingest.py and deploy_stepfunctions.py.

    Attaches two things: the AWS-managed AWSGlueServiceRole policy (just
    enough for Glue itself to run a job and write CloudWatch Logs — the
    Glue equivalent of AWSLambdaBasicExecutionRole for Lambda), plus an
    inline policy scoped to exactly this job's S3 read/write needs."""
    role_name = config["job_role_name"]
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"IAM role '{role_name}' already exists — reusing it.")
        role_is_new = False
    except iam.exceptions.NoSuchEntityException:
        trust_policy = load_json(TRUST_POLICY_PATH)
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for the {config['job_name']} Glue job",
        )["Role"]
        print(f"Created IAM role '{role_name}'.")
        role_is_new = True

    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
    )

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{config['job_name']}-s3-access",
        PolicyDocument=json.dumps(build_s3_policy(config)),
    )
    print(f"Attached Glue + S3 permissions to '{role_name}'.")

    if role_is_new:
        print("Waiting 10s for the new role to finish propagating...")
        time.sleep(10)

    return role["Arn"]


def upload_script(s3, config):
    """Glue jobs don't read code from your repo directly — they read it
    from S3. This uploads the current local copy of the transform script
    every time the deploy script runs, so the S3 copy can never silently
    drift from what's in the repo (the same class of problem the Lambda's
    console-paste workflow had, avoided the same way here from the start)."""
    local_path = REPO_ROOT / config["script_local_path"]
    s3.upload_file(
        str(local_path),
        config["script_s3_bucket"],
        config["script_s3_key"],
    )
    print(f"Uploaded {config['script_local_path']} to s3://{config['script_s3_bucket']}/{config['script_s3_key']}")


def deploy_job(glue, config, role_arn):
    name = config["job_name"]
    script_location = f"s3://{config['script_s3_bucket']}/{config['script_s3_key']}"

    job_kwargs = dict(
        Role=role_arn,
        Command={
            "Name": "pythonshell",
            "ScriptLocation": script_location,
            "PythonVersion": config["python_version"],
        },
        GlueVersion=config["glue_version"],
        MaxCapacity=config["max_capacity"],
        Timeout=config["timeout_minutes"],
        DefaultArguments={
            # Lets the job install pyarrow at startup — needed for
            # pandas.to_parquet(), and not one of Glue Python Shell's
            # pre-installed libraries (pandas and numpy are; pyarrow isn't).
            "--additional-python-modules": config["additional_python_modules"],
            # Passed as job parameters rather than hardcoded in the script,
            # for the same reason every other config value in this project
            # lives in JSON rather than in code: change the bucket or
            # prefix here, not by editing and redeploying the script.
            "--raw_bucket": config["raw_s3_bucket"],
            "--raw_prefix": config["raw_s3_prefix"],
            "--curated_bucket": config["curated_s3_bucket"],
            "--curated_prefix": config["curated_s3_prefix"],
        },
    )

    try:
        glue.get_job(JobName=name)
        exists = True
    except glue.exceptions.EntityNotFoundException:
        exists = False

    if not exists:
        glue.create_job(Name=name, **job_kwargs)
        print(f"Created Glue job '{name}'.")
        return

    glue.update_job(JobName=name, JobUpdate=job_kwargs)
    print(f"Updated existing Glue job '{name}'.")


def main():
    config = load_json(CONFIG_PATH)
    session = boto3.Session(region_name=config["region"])
    iam = session.client("iam")
    s3 = session.client("s3")
    glue = session.client("glue")

    role_arn = ensure_role(iam, config)
    upload_script(s3, config)
    deploy_job(glue, config, role_arn)

    print(
        "Done. Run a manual test from the Glue console (Jobs → select the "
        "job → Run), or wait for the Step Functions workflow to trigger it "
        "as part of the next scheduled run."
    )


if __name__ == "__main__":
    main()
