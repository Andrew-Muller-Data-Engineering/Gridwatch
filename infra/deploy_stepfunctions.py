"""
Deploys the Step Functions state machine and its EventBridge schedule
straight from the repo — the same boto3-deploy pattern used for the
Lambda in deploy_neso_ingest.py, extended to cover the rest of Phase 2.

Safe to re-run: creates everything fresh the first time, updates
everything in place on every run after that.

Also fills in the AWS account ID in infra/neso_ingest_state_machine.json
automatically (by asking AWS who you are via STS), so you no longer need
to manually replace YOUR_ACCOUNT_ID by hand before deploying.

Run from the repo root, in VS Code's integrated terminal (.venv
activated), after deploy_neso_ingest.py and deploy_glue_transform.py have
already been run at least once (the Lambda and the Glue job themselves
must exist first, since the state machine invokes/starts them by name):

    python infra/deploy_stepfunctions.py
"""

import json
import pathlib
import time

import boto3

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INFRA_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = INFRA_DIR / "neso_ingest_stepfunctions_config.json"
SFN_TRUST_POLICY_PATH = INFRA_DIR / "neso_ingest_stepfunctions_trust_policy.json"
SCHEDULER_TRUST_POLICY_PATH = INFRA_DIR / "neso_ingest_scheduler_trust_policy.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ensure_role(iam, role_name, trust_policy_path, inline_policy_name, inline_policy_document, description):
    """Creates the role if it doesn't exist yet, and (re)applies its
    inline permission policy either way — same pattern as
    deploy_neso_ingest.py's ensure_role(), generalized so both the state
    machine's role and the schedule's role can share this logic."""
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"IAM role '{role_name}' already exists — reusing it.")
        role_is_new = False
    except iam.exceptions.NoSuchEntityException:
        trust_policy = load_json(trust_policy_path)
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
        )["Role"]
        print(f"Created IAM role '{role_name}'.")
        role_is_new = True

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=inline_policy_name,
        PolicyDocument=json.dumps(inline_policy_document),
    )
    print(f"Attached '{inline_policy_name}' to '{role_name}'.")

    if role_is_new:
        # Same IAM eventual-consistency accommodation as the Lambda script.
        print("Waiting 10s for the new role to finish propagating...")
        time.sleep(10)

    return role["Arn"]


def build_state_machine_policy(lambda_arn, glue_job_arn, glue_managed_rule_arn):
    """The state machine's workflow now has two steps — invoke the Lambda,
    then run the Glue job — so its role needs permission for both, each
    scoped to the one specific resource it needs, not a wildcard:

    - lambda:InvokeFunction, scoped to this one Lambda's ARN.
    - glue:StartJobRun / GetJobRun(s) / BatchStopJobRun, scoped to this one
      Glue job's ARN — the actions needed to start a Glue job and monitor
      it to completion.
    - events:PutRule / PutTargets / DescribeRule, scoped to a single,
      specific EventBridge rule AWS itself creates and manages
      (StepFunctionsGetEventForGlueJobRunRule) purely as internal plumbing
      for the ".sync" integration pattern below — Step Functions uses this
      rule to know when the Glue job finishes, rather than polling.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arn,
            },
            {
                "Effect": "Allow",
                "Action": [
                    "glue:StartJobRun",
                    "glue:GetJobRun",
                    "glue:GetJobRuns",
                    "glue:BatchStopJobRun",
                ],
                "Resource": glue_job_arn,
            },
            {
                "Effect": "Allow",
                "Action": [
                    "events:PutRule",
                    "events:PutTargets",
                    "events:DescribeRule",
                ],
                "Resource": glue_managed_rule_arn,
            },
        ],
    }


def build_start_execution_policy(state_machine_arn):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "states:StartExecution",
                "Resource": state_machine_arn,
            }
        ],
    }


def deploy_state_machine(sfn, config, role_arn, account_id):
    definition_path = REPO_ROOT / config["state_machine_definition_file"]
    definition_text = definition_path.read_text().replace("YOUR_ACCOUNT_ID", account_id)
    # Validate it's well-formed JSON before sending it to AWS, so a typo
    # in the definition file fails fast with a clear error here rather
    # than a confusing one from the Step Functions API.
    json.loads(definition_text)

    name = config["state_machine_name"]
    state_machine_arn = f"arn:aws:states:{config['region']}:{account_id}:stateMachine:{name}"

    try:
        sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        exists = True
    except sfn.exceptions.StateMachineDoesNotExist:
        exists = False

    if not exists:
        sfn.create_state_machine(
            name=name,
            definition=definition_text,
            roleArn=role_arn,
            type="STANDARD",
        )
        print(f"Created state machine '{name}'.")
        return state_machine_arn

    sfn.update_state_machine(
        stateMachineArn=state_machine_arn,
        definition=definition_text,
        roleArn=role_arn,
    )
    print(f"Updated existing state machine '{name}'.")
    return state_machine_arn


def deploy_schedule(scheduler, config, state_machine_arn, schedule_role_arn):
    name = config["schedule_name"]
    target = {"Arn": state_machine_arn, "RoleArn": schedule_role_arn}
    # Optional: without this, cron expressions are evaluated in UTC, which
    # silently drifts by an hour whenever UK clocks change for BST/GMT.
    # Setting an explicit IANA timezone name here means "9am" always means
    # 9am in that zone, year-round, with no seasonal adjustment needed.
    timezone = config.get("schedule_expression_timezone")

    try:
        scheduler.get_schedule(Name=name)
        exists = True
    except scheduler.exceptions.ResourceNotFoundException:
        exists = False

    kwargs = dict(
        Name=name,
        ScheduleExpression=config["schedule_expression"],
        FlexibleTimeWindow={"Mode": "OFF"},
        Target=target,
    )
    if timezone:
        kwargs["ScheduleExpressionTimezone"] = timezone

    if not exists:
        scheduler.create_schedule(**kwargs)
        print(f"Created EventBridge schedule '{name}'.")
        return

    scheduler.update_schedule(**kwargs)
    print(f"Updated existing EventBridge schedule '{name}'.")


def main():
    config = load_json(CONFIG_PATH)
    session = boto3.Session(region_name=config["region"])
    iam = session.client("iam")
    sts = session.client("sts")
    sfn = session.client("stepfunctions")
    scheduler = session.client("scheduler")
    lambda_client = session.client("lambda")

    account_id = sts.get_caller_identity()["Account"]

    lambda_arn = lambda_client.get_function(FunctionName=config["lambda_function_name"])["Configuration"][
        "FunctionArn"
    ]
    glue_job_arn = f"arn:aws:glue:{config['region']}:{account_id}:job/{config['glue_job_name']}"
    glue_managed_rule_arn = (
        f"arn:aws:events:{config['region']}:{account_id}:rule/StepFunctionsGetEventForGlueJobRunRule"
    )

    # The state machine's own role: allowed to invoke exactly one Lambda
    # and run exactly one Glue job, nothing else — same least-privilege
    # pattern as every other role in this project.
    sfn_role_arn = ensure_role(
        iam,
        config["state_machine_role_name"],
        SFN_TRUST_POLICY_PATH,
        f"{config['state_machine_name']}-invoke-lambda-and-glue",
        build_state_machine_policy(lambda_arn, glue_job_arn, glue_managed_rule_arn),
        f"Execution role for the {config['state_machine_name']} state machine",
    )

    state_machine_arn = deploy_state_machine(sfn, config, sfn_role_arn, account_id)

    # The schedule's own role: allowed to start exactly one state
    # machine's executions, nothing else.
    schedule_role_arn = ensure_role(
        iam,
        config["schedule_role_name"],
        SCHEDULER_TRUST_POLICY_PATH,
        f"{config['schedule_name']}-start-execution",
        build_start_execution_policy(state_machine_arn),
        f"Execution role for the {config['schedule_name']} EventBridge schedule",
    )

    deploy_schedule(scheduler, config, state_machine_arn, schedule_role_arn)

    print(
        "Done. Check the state machine and schedule in the AWS console, "
        "or trigger a manual execution to confirm the whole chain works."
    )


if __name__ == "__main__":
    main()
