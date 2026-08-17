# GridWatch — `infra/` Cheatsheet

A quick-reference for every file in `infra/` — what it is, what it does, and whether you'd ever need to touch it. Every AWS resource GridWatch manages follows the same three-file pattern: one JSON file holding its **settings**, one JSON file holding its **trust policy** (who's allowed to use it), and one Python script that actually **deploys** it by reading the other two. Once you recognize that shape, every new file added here should slot into one of those three roles.

Updated as new resources are added — currently covers the Lambda (Phase 2) and the Step Functions + EventBridge schedule (Phase 2).

---

## Quick reference

| File | Role | Edit it when... |
|---|---|---|
| `neso_ingest_lambda_config.json` | Lambda settings | You rename the function, change its bucket, memory, or timeout |
| `neso_ingest_trust_policy.json` | Lambda's trust policy | Basically never — static |
| `deploy_neso_ingest.py` | Deploys the Lambda | Rarely — only if the deploy *logic* itself needs to change |
| `neso_ingest_state_machine.json` | Step Functions workflow definition | You change the workflow itself (add a state, change retry behaviour) |
| `neso_ingest_stepfunctions_config.json` | State machine + schedule settings | You rename things, change the schedule cadence |
| `neso_ingest_stepfunctions_trust_policy.json` | State machine's trust policy | Basically never — static |
| `neso_ingest_scheduler_trust_policy.json` | Schedule's trust policy | Basically never — static |
| `deploy_stepfunctions.py` | Deploys the state machine + schedule | Rarely — only if the deploy logic itself needs to change |

You'll run the two `deploy_*.py` scripts often (every time you change code or workflow logic); everything else gets edited occasionally and read even less often — which is exactly why this cheatsheet exists.

---

## Lambda deploy (Phase 2, part 1)

### `neso_ingest_lambda_config.json`
**What it is:** plain settings for the Lambda function — function name, IAM role name, the `module.function` handler path, Python runtime version, timeout, memory, region, the S3 bucket it writes to, and the local path to its code.

**Why it's a separate file:** keeps "what this Lambda is configured as" declarative and readable, rather than buried as arguments inside the deploy script. Anyone (including future you) can see the Lambda's whole config at a glance without reading Python.

**Gotcha worth remembering:** `s3_bucket` here is a *second, separate copy* of the bucket name — the real one lives in `handler.py`'s `S3_BUCKET` constant, since that's what the Lambda actually reads at runtime. This file's copy is only used at *deploy time*, to build the IAM policy that grants write access to that bucket. The two must match exactly, or the Lambda gets `AccessDenied` (ask me about the afternoon this taught us that, if you ever forget why).

### `neso_ingest_trust_policy.json`
**What it is:** a minimal IAM trust policy saying "only the Lambda service (`lambda.amazonaws.com`) may assume this role." Distinct from a *permissions* policy (which says what the role can *do*) — this one only says *who* can use it.

**Why it's static:** it never needs to change unless you're doing something unusual (e.g. letting a different AWS service assume the same role), which this project doesn't.

### `deploy_neso_ingest.py`
**What it does, in order:** creates (or reuses) the IAM role from the trust policy above, attaches CloudWatch Logs access plus an S3-write permission built from `neso_ingest_lambda_config.json`'s bucket name, zips up `handler.py`, then creates the Lambda function fresh (first run) or pushes updated code and settings to it (every run after).

**When you run it:** every time you change `handler.py`, or the very first time to create everything from nothing. It's idempotent — safe to run as many times as you like.

---

## Step Functions + EventBridge deploy (Phase 2, part 2)

### `neso_ingest_state_machine.json`
**What it is:** the actual workflow definition, written in Amazon States Language (ASL) — a JSON-based format. GridWatch's version is deliberately simple: one state, `InvokeNesoIngestLambda`, which calls the Lambda with automatic retries (3 attempts, exponential backoff) if it fails.

**Why it's separate from the deploy script:** this is the one file in this whole folder that describes actual *business logic* (the shape of the workflow) rather than deployment mechanics — worth keeping visually distinct so it's obvious where to look if you ever add a second step to the pipeline (e.g. a future distribution-level Lambda running alongside this one).

**Note:** it contains a `YOUR_ACCOUNT_ID` placeholder in the Lambda's ARN. `deploy_stepfunctions.py` fills this in automatically at deploy time by asking AWS who you are (via STS) — you never need to hand-edit this file to insert your real account ID.

### `neso_ingest_stepfunctions_config.json`
**What it is:** settings for *two* resources at once — the state machine (name, its IAM role's name, where to find its definition file) and the EventBridge schedule (name, its own IAM role's name, and the cadence — currently `rate(1 day)`).

**Why one config file for two resources:** they're deployed together by the same script and conceptually inseparable (a schedule with nothing to trigger is meaningless) — splitting them into two config files would just mean more files to keep in sync for no real benefit.

### `neso_ingest_stepfunctions_trust_policy.json`
**What it is:** the trust policy for the state machine's execution role — "only the Step Functions service (`states.amazonaws.com`) may assume this role."

### `neso_ingest_scheduler_trust_policy.json`
**What it is:** the trust policy for the *schedule's* execution role — "only EventBridge Scheduler (`scheduler.amazonaws.com`) may assume this role." A separate file from the one above because it's a genuinely different principal trusting a genuinely different role for a genuinely different purpose (starting executions, vs. running the workflow itself).

### `deploy_stepfunctions.py`
**What it does, in order:**
1. Looks up your AWS account ID and the Lambda's ARN automatically (no manual copy-paste needed).
2. Creates/updates the state machine's role, scoped to just `lambda:InvokeFunction` on that one Lambda.
3. Creates or updates the state machine itself from `neso_ingest_state_machine.json`.
4. Creates/updates the schedule's role, scoped to just `states:StartExecution` on that one state machine.
5. Creates or updates the EventBridge schedule itself, pointing at the state machine.

**Prerequisite:** the Lambda must already exist (run `deploy_neso_ingest.py` first) — this script looks up its ARN by name and would fail if it isn't there yet.

**When you run it:** after any change to the workflow definition or the schedule cadence, or the first time to create everything.

---

## The pattern, summarized

Every AWS resource GridWatch manages this way follows the same shape: a **role gets a trust policy** (who can become it) **and a permissions policy** (what it can then do, scoped as narrowly as possible), and a **deploy script ties it all together**, reading the config so nothing is hardcoded inside the Python itself. Recognizing this shape means a third resource (say, a future Glue job in Phase 3) should be a fairly mechanical extension of the same three-file pattern, not a new problem to solve from scratch.
