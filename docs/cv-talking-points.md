# GridWatch — Engineering Decisions & Interview Talking Points

A running log of the reasoning behind specific technical decisions made while building GridWatch — not the CV bullets themselves (those are in the build guide's "Skills this demonstrates" table), but the deeper *why* behind them, in a form you can pull from for interview answers when someone asks "walk me through a decision you made" or "tell me about a trade-off." Added to as the project progresses.

---

## 1. IAM users vs. IAM roles — least privilege in practice

**The concept:** an IAM *user* represents a person — you, logging in via the console or the CLI with long-lived credentials. An IAM *role* is a different kind of identity entirely: not a person, but something a trusted service or account can *temporarily assume*. A role has two separate kinds of policy attached to it, answering two separate questions:
- **Trust policy** (`AssumeRolePolicyDocument`) — *who* is allowed to assume this role. GridWatch's Lambda role trusts exactly one principal: `lambda.amazonaws.com` — the Lambda service itself, nothing else.
- **Permission policies** — *what* the role can do once assumed. Scoped here to `s3:PutObject` on one specific bucket, plus the AWS-managed `AWSLambdaBasicExecutionRole` (CloudWatch Logs write).

**What this means in practice for GridWatch:** deploying new code (running `infra/deploy_neso_ingest.py`) uses *your* IAM user's admin credentials — the role isn't involved in that step at all. The role only comes into play once the function is actually *running*: every AWS call `handler.py` makes at runtime (its one `s3.put_object(...)` call) executes under the role's permissions, not yours.

**Why it matters — the actual risk being managed:** if the function's code were ever compromised while running — a vulnerable dependency, a bug an attacker could exploit — the damage it could do is capped by what the role allows: write to one S3 bucket, write logs, and nothing else. Compare that to what would happen if the function somehow executed with your admin user's own permissions instead: full account access. That gap is the entire point of the principle of least privilege — the blast radius of a compromised runtime is bounded by the narrowest role that still lets it do its job, deliberately kept separate from the broader permissions a human operator needs.

**Interview-ready framing:** *"I gave the Lambda its own execution role with least-privilege access — scoped to a single `s3:PutObject` permission on one bucket plus basic logging — deliberately separate from my own admin IAM user, so that even if the function's code were compromised at runtime, the blast radius is capped at 'write to one bucket,' not 'do anything my AWS account can do.'"*

---

## 2. Deploying from the repo instead of the AWS Console

**The concept:** the original Phase 2 plan was to paste `handler.py` directly into the Lambda console's inline code editor — the simplest possible first deploy, no packaging, no tooling. The trade-off: the console becomes the actual source of truth for what's running. Edit code there and forget to copy it back into the repo, and the repo silently drifts out of sync with reality.

**What changed:** `infra/deploy_neso_ingest.py`, a small boto3 script that reads declarative config (`infra/neso_ingest_lambda_config.json`, `infra/neso_ingest_trust_policy.json`) and pushes the handler code and its AWS configuration (runtime, memory, timeout, IAM role and permissions) to AWS programmatically. Idempotent by design — it checks whether the role/function already exist and switches between "create" and "update" accordingly, so it's safe to re-run after every code change.

**Why it matters:** every deploy is now a `git`-trackable action — the repo is unambiguously the source of truth, and the console becomes somewhere to *observe* the function (logs, test invocations), not edit it. This is deliberately not a full infrastructure-as-code framework (AWS SAM or CDK would be the "proper" next step — templated, with drift detection and rollback) — it's a lighter-weight version of the same underlying idea, appropriate for a single Lambda, with a clear line to what a bigger version of this would look like.

**Interview-ready framing:** *"I moved from console-based deployment to a boto3 script that reads the Lambda's configuration from version-controlled JSON in the repo — not a full IaC framework, but it removes the console as a hidden source of truth, which was the actual problem worth solving at this scale."*

---

## 3. IAM eventual consistency

**The concept:** IAM is a globally distributed service — when you create a new role, that change has to propagate across AWS's infrastructure before every service can reliably see and use it. For a few seconds after creation, a role can exist from IAM's perspective but not yet be usable by, say, the Lambda service trying to create a function with it — an `InvalidParameterValueException` that looks like a bug but isn't.

**What this means in practice:** `deploy_neso_ingest.py` waits 10 seconds after creating a *new* role before trying to use it to create the Lambda function (existing roles skip this wait entirely — it's only relevant the very first time). A pragmatic accommodation, not a design flaw.

**Why it matters:** it's a genuinely common gotcha in real infrastructure automation — any script or CI/CD pipeline that creates an IAM identity and immediately tries to use it needs to account for this, either with a short wait or a retry loop. Knowing to expect it (rather than being caught out by a flaky-looking failure) is a small but real signal of hands-on AWS experience.

**Interview-ready framing:** *"My first version of the deploy script intermittently failed right after creating a new IAM role, because IAM changes aren't instantly consistent across AWS — I added a short wait after role creation to account for that propagation delay."*

---

## 4. Debugging a persistent AccessDenied — isolating variables systematically

**The situation:** the Lambda's `s3.put_object()` call failed with a generic `AccessDenied` — the least informative error AWS gives, since it's returned for identity-policy denials, bucket-policy denials, cross-account issues, encryption issues, and more, all with identical wording. Every individual check looked correct in isolation, which made this a genuinely hard bug rather than a simple misconfiguration.

**The method — ruling things out one variable at a time, cheapest checks first:**
1. Confirmed the function's execution role was actually the intended one (not a leftover console-auto-generated role with a similar name).
2. Read the role's actual inline policy JSON directly, rather than trusting a summary view — confirmed `Effect: Allow`, `Action: s3:PutObject`, `Resource` scoped correctly.
3. Ruled out bucket-side causes that sit outside IAM entirely: no bucket policy, ACLs (which can only grant, never deny), and default encryption (SSE-S3, not a KMS key requiring extra permissions).
4. Confirmed the CLI and console were operating in the same AWS account (ruling out a cross-account bucket-ownership mismatch).
5. Used the **IAM Policy Simulator** to get AWS's own authoritative answer on whether the policy allowed the action — it said yes, once the simulation was correctly scoped to the real resource ARN rather than a wildcard.
6. **Isolated bucket vs. role** by writing to the same bucket with a completely different, known-good identity (the admin IAM user, via `aws s3 cp`) — it succeeded, proving the bucket itself had no inherent problem.
7. **Isolated "insufficient scope" vs. "something else entirely"** by temporarily attaching the broadest possible AWS-managed S3 policy (`AmazonS3FullAccess`) to the role as a control test — it *still* failed, which was the critical result: it proved the problem couldn't be about policy scope at all, since even unlimited scope didn't fix it.
8. With every policy-based explanation exhausted, added direct runtime introspection — a single `print("Running as:", sts.get_caller_identity())` at the top of the handler — to see, with certainty, what AWS believed was happening at the exact moment of failure, rather than continuing to reason from the outside.
9. **Root cause:** an unrelated git operation had silently reverted the local `handler.py` back to an earlier saved version — one still carrying the original placeholder `S3_BUCKET = "your-bucket-name"` instead of the real bucket name. The Lambda had been faithfully, correctly denied access the entire time — to a bucket it never should have had permission to, because that placeholder name wasn't a bucket anyone had actually granted it.

**Why it matters:** the broad-access control test (step 7) was the pivotal moment — it's what proved the issue wasn't really about IAM at all, and redirected the entire investigation away from permissions and toward "what code is actually running." It's a reusable debugging principle: when a fix that *should* obviously work doesn't, stop refining the fix and start questioning the assumption underneath it — in this case, the unstated assumption that the deployed code matched the code being read and reasoned about.

**Interview-ready framing:** *"I hit a persistent AccessDenied on an S3 write that survived a correct, Policy-Simulator-verified IAM policy — I isolated the cause by testing with a different identity (proved the bucket was fine), then temporarily granting the role unlimited S3 access as a control (proved it wasn't a scope problem at all). That pointed away from permissions entirely, so I added direct runtime logging to see the actual state at the point of failure — which revealed the deployed code had silently drifted from what I thought was deployed, due to an unrelated git operation reverting a local file. The bug wasn't a wrong permission; it was a wrong assumption about what code was even running."*

---

## 5. IAM roles for cross-service invocation — chained, narrowly-scoped delegation

**The concept:** Phase 2's pipeline isn't just one AWS service calling AWS on your behalf — it's three services calling *each other*, in a chain: EventBridge Scheduler starts a Step Functions execution, which invokes a Lambda, which writes to S3. Each link in that chain is a different AWS service assuming a role to act, and — following the same principle as the Lambda's own role — each of those roles is scoped to do exactly one thing and nothing else:
- The **Lambda's role** can `s3:PutObject` on one bucket, nothing more (Entry 1).
- The **state machine's role** can `lambda:InvokeFunction`, scoped by `Resource` to that one Lambda's ARN. It cannot invoke any other function in the account, even though the trust policy lets Step Functions assume the role at all.
- The **schedule's role** can `states:StartExecution`, scoped by `Resource` to that one state machine's ARN. It cannot start any other state machine.

**What this means in practice for GridWatch:** `infra/deploy_stepfunctions.py`'s `ensure_role()` function is deliberately generic — it creates a role from a trust policy and attaches an inline permission policy, and it's called twice with two completely different trust policies (`states.amazonaws.com`, `scheduler.amazonaws.com`) and two completely different permission policies (`build_invoke_lambda_policy`, `build_start_execution_policy`). Same shape, reused, because the underlying pattern — a role that trusts one specific service and can do one specific narrowly-scoped thing — doesn't change; only the specific service and the specific permission do.

**Why it matters:** this is what "least privilege" looks like once a pipeline has more than one moving part — it isn't a single decision made once, it's a discipline applied at every hop. If the schedule's role were accidentally given `states:StartExecution` on `*` instead of one ARN, an attacker (or a bug) that gained control of the schedule could kick off *any* state machine in the account, not just this one. Scoping every role to a specific `Resource` ARN, not a wildcard, is what keeps a compromise at any single link contained to that link.

**Interview-ready framing:** *"The pipeline chains three AWS services calling each other — EventBridge starts Step Functions, which invokes Lambda — so I gave each hop its own IAM role, scoped by resource ARN to the one specific thing it needs to do next, rather than one broad role shared across the chain. My deploy script's role-creation logic is generic and reused for both roles, since the pattern — narrow trust, narrow permission — is identical each time; only the service and the action change."*

---

## 6. `rate()` vs. `cron()` — choosing a schedule that means what you think it means

**The situation:** the original EventBridge schedule used `rate(1 day)` — simple, and it worked. But "every 24 hours" and "every day at a specific time" are not the same guarantee: a `rate()` expression is anchored to whenever the schedule happened to be *created*, not to any clock time, so it drifts to whatever time of day that was — fine for a first test, not what you'd actually want for something meant to double as a daily reporting feed, where a predictable, fixed time of day (9am, standard for reporting) matters more than the exact interval between runs.

**The fix:** switched to `cron(0 9 * * ? *)` — an exact "minute 0 of hour 9, every day" — plus an explicit `ScheduleExpressionTimezone: "Europe/London"` on the schedule. The timezone setting is the part that's easy to miss: a bare `cron()` expression is evaluated in UTC, so without it, "9am" silently becomes "9am UTC," which is 9am UK time in winter (GMT) but 10am UK time in summer (BST) — a schedule that quietly runs an hour "wrong" for half the year unless you notice.

**Why it matters:** it's a small, specific example of a broader class of scheduling bug — one that's easy to introduce and easy not to notice, since it only manifests as an hour's drift twice a year around the clock changes, not as an obvious failure. Choosing `cron()` with an explicit IANA timezone name over a `rate()` expression is a deliberate trade (a few more characters of config) for a schedule that actually means "9am, always" rather than "roughly once a day, at a time that happens to drift."

**Interview-ready framing:** *"I initially scheduled the pipeline with a `rate(1 day)` expression, which just repeats every 24 hours from creation time rather than running at a fixed clock time. Since this was meant to model a daily reporting feed, I switched to a `cron()` expression with an explicit timezone instead — otherwise the schedule would silently drift by an hour every time UK clocks change for BST or GMT, since cron expressions are evaluated in UTC by default."*

---

## 7. Choosing Glue Python Shell over Spark — matching compute to actual workload

**The concept:** AWS Glue's headline offering is Spark-based ETL — genuinely built for large-scale distributed data processing, and it's what most people picture when they hear "AWS Glue." But Spark jobs spin up a small cluster to run, which costs real money whether the dataset is a terabyte or, as in GridWatch's case, 18 small JSON records fetched once a day. **Glue Python Shell** is a different job type entirely — a single lightweight Python process, no cluster — billed at Glue's smallest compute tier (0.0625 DPU, a fraction of Glue's already-small unit of compute) rather than whatever a Spark cluster's minimum footprint would cost.

**What this means in practice for GridWatch:** `infra/neso_transform_glue_config.json` sets `"max_capacity": 0.0625` and the job's `Command.Name` to `"pythonshell"` rather than `"glueetl"` (Spark). The transform logic itself (`transform/glue_jobs/clean_neso_data.py`) is plain `pandas`/`pyarrow`, not PySpark — appropriate for a dataset this small, and it still counts as real, hands-on AWS Glue experience, since the service, the job type, and the deployment pattern are all genuinely Glue, not a workaround that avoids it.

**Why it matters:** this is a deliberate example of matching infrastructure choice to actual data volume, rather than defaulting to whichever tool has the most name recognition. Glue ETL (Spark) would work here — it just wouldn't be a good decision, since it solves a scaling problem this project doesn't have, at a cost this project doesn't need to pay. Recognizing when a "bigger" tool is the wrong tool is as much a signal of real engineering judgment as knowing how to use the bigger tool at all.

**Interview-ready framing:** *"I chose Glue Python Shell over Glue's Spark-based ETL jobs for the transform layer, since the actual daily data volume — a couple of dozen small JSON readings — doesn't need distributed processing, and a Spark cluster's minimum footprint would have been paying for scale I didn't need. Python Shell runs as a single lightweight process at Glue's smallest compute tier, while still being genuine, billable AWS Glue rather than a workaround."*

---

## 8. Step Functions' `.sync` integration — and the IAM permissions it quietly requires

**The situation:** chaining the Glue transform job into the existing Step Functions workflow looked, at first glance, like it should need only one new permission — `glue:StartJobRun` on the state machine's role, so it could kick the job off. That's not quite enough for a *meaningful* result, though: without more, Step Functions would mark that state "succeeded" the instant the Glue API confirmed the job had *started*, regardless of whether the job then went on to actually finish or fail a minute later.

**The fix — the `.sync` suffix:** changing the state's `Resource` from `arn:aws:states:::glue:startJobRun` to `arn:aws:states:::glue:startJobRun.sync` tells Step Functions to actually wait for the Glue job to reach a terminal state (succeeded or failed) before marking its own state complete, and to propagate a failure if the Glue job fails. Functionally, this is the difference between "did I *start* the transform" and "did the transform *work*" — the second one is the actual thing worth knowing.

**The IAM cost of that convenience:** `.sync` isn't free in permissions terms — AWS implements it under the hood using a managed EventBridge rule (`StepFunctionsGetEventForGlueJobRunRule`) that Step Functions creates and uses to get notified when the Glue job finishes, rather than polling in a loop. That means the state machine's role needs `glue:GetJobRun`/`GetJobRuns`/`BatchStopJobRun` (to check status and, if needed, stop a stuck job) *and* `events:PutRule`/`PutTargets`/`DescribeRule` scoped to that one specific managed rule — permissions that have nothing to do with Glue directly, and are easy to miss if you're reasoning only about "what does this state need to call."

**Why it matters:** it's a concrete example of a service integration's convenience (`.sync` doing the polling for you) coming with implementation details that leak into what IAM permissions you actually need — the kind of thing you only really learn by hitting it, not by reading the state's definition in isolation. Knowing to look for this — rather than being surprised by an `AccessDenied` on a permission that seems unrelated to the task at hand — is a genuinely useful pattern-recognition skill for AWS service integrations generally, not just this one.

**Interview-ready framing:** *"When I added a Glue job as a second step in an existing Step Functions workflow, I used the `.sync` integration pattern so the workflow would actually wait for the job to finish rather than just confirming it started. That meant the state machine's role needed more than `glue:StartJobRun` — `.sync` uses a managed EventBridge rule under the hood to detect job completion, so the role also needed narrowly-scoped `events:PutRule`/`PutTargets`/`DescribeRule` permissions on that specific rule. It's a good example of a service integration's internal mechanics surfacing as IAM requirements you wouldn't guess from the state's definition alone."*

---

## 9. Choosing a cross-cloud bridge deliberately — and rejecting two real alternatives

**The concept:** AWS and GCP don't share storage — moving Phase 3's curated Parquet from S3 into BigQuery meant an explicit decision about *how* to cross that boundary, unlike every earlier phase, which stayed inside AWS entirely. Two genuine alternatives existed and were deliberately rejected, not overlooked: **BigQuery Omni** would let BigQuery query the S3 data in place with zero data movement — the most elegant option on paper, but it requires BigQuery Enterprise/Enterprise Plus edition, real recurring cost outside this project's always-free scope. **GCP's Storage Transfer Service** would pull from S3 on a schedule with no custom code at all — but it needs AWS access keys stored as a GCP-side credential (a second long-lived cross-cloud secret to manage, on top of the one the chosen approach already needed) and its own per-job cost and scheduling model.

**What was built instead:** a plain script — download from S3, re-upload to GCS, load into BigQuery — following the exact same config-plus-deploy-script shape as every AWS resource already in the project, first proven manually from a laptop, then ported into a Lambda for automation once the underlying logic was trusted.

**Why it matters:** this is the same shape of decision as Glue Python Shell vs. Spark in Phase 3 — evaluating the "proper," more powerful-looking option and consciously choosing simpler and cheaper because it actually fits the problem's real scale, rather than defaulting to whichever tool sounds most sophisticated on a CV.

**Interview-ready framing:** *"AWS and GCP don't share storage, so bridging curated data into BigQuery needed an explicit decision, not just another deploy script. I evaluated BigQuery Omni (query S3 data in place, but requires a paid BigQuery edition) and GCP's Storage Transfer Service (managed, but needs AWS keys stored as a GCP credential and its own scheduling overhead) and rejected both in favor of a straightforward script — proven manually first, then automated — that fit the project's actual data volume and stayed inside the always-free tier on both clouds."*

---

## 10. One afternoon, three services, three different permission granularities

**The situation:** getting the automated cross-cloud Lambda working meant debugging IAM-style permission errors from three genuinely different systems, back to back, each with its own idea of how "read" or "write" access should be scoped:

1. **AWS S3:** the Lambda's role had `s3:GetObject` (needed to read a file) but not `s3:ListBucket` (needed to enumerate which files exist) — and critically, those two actions require *differently-shaped* `Resource` ARNs: `GetObject` needs an object-level ARN (`bucket/key`), while `ListBucket` needs the bucket-level ARN itself, with an `s3:prefix` condition to keep it narrowly scoped rather than the wildcard grant it might look like it needs.
2. **GCP Cloud Storage:** granting `roles/storage.objectCreator` seemed right for "this job writes files here" — until it turned out overwriting an *existing* object (which a daily re-run legitimately needs to do) requires delete permission on the previous version too, something Creator deliberately excludes. `roles/storage.objectAdmin` was the actual fit.
3. **BigQuery:** the newer `bq add-iam-policy-binding` command for granting dataset-level access failed outright with "this feature requires allowlisting" — an unrelated Google-side rollout gate, not a permissions problem at all. The fix was falling back to BigQuery's older, still fully-supported dataset **Sharing** panel in the console, which uses BigQuery's own long-standing ACL system rather than the newer Cloud-IAM-integrated path.

**Why it matters:** none of these were the same bug wearing a different name — each one was a genuinely distinct permission model with its own granularity, its own required resource shape, and in one case, its own separate rollout status across projects. The pattern worth taking away isn't a specific fix, it's the instinct: when a permission error shows up, don't assume it behaves like the last cloud's permission error — go find that specific service's own model for what "least privilege" means there.

**Interview-ready framing:** *"Wiring up a Lambda that touches AWS S3, GCP Cloud Storage, and BigQuery in one run meant hitting three separately-scoped permission errors in one afternoon — S3 needing a bucket-level ARN for ListBucket versus an object-level one for GetObject, GCS's object-creator role not covering overwrites, and BigQuery's newer IAM-binding command being allowlist-gated on that project, requiring the older Sharing-panel fallback. It reinforced that 'least privilege' isn't one concept portable across services — each one has its own model, and debugging it well means learning that model rather than pattern-matching from the last one."*

---

## 11. A deliberate, documented trade-off: static credential now, keyless later

**The situation:** the automated Lambda needs to authenticate to GCP somehow. The modern, best-practice answer is Workload Identity Federation (WIF) — the Lambda's own short-lived AWS credentials get exchanged for a short-lived GCP token at runtime, with no long-lived secret stored anywhere, ever. The simpler answer is a GCP service account key: a static JSON credential, stored in AWS Secrets Manager, fetched at runtime. WIF was consciously set aside in favor of the key — a real trade-off, not an oversight, made explicit up front rather than discovered as a limitation later.

**An unexpected twist:** Google's own defaults nearly forced the decision anyway — `gcloud iam service-accounts keys create` failed outright with `FAILED_PRECONDITION: Key creation is not allowed on this service account`, a newer default on GCP projects specifically designed to push people toward WIF instead of static keys. After confirming the constraint was genuinely locked at the project level (not something an org-policy override could fix here), the key still turned out to be creatable through the console's own UI rather than the CLI — a useful reminder that a blocked CLI path and a blocked *capability* aren't automatically the same thing, worth actually verifying before assuming a fallback plan is necessary.

**Why it matters:** the honest trade-off here — "static key now, deliberately, with a clear path to something better later" — is a more credible answer in an interview than either pretending WIF was too complicated to consider, or building it under pressure without being able to explain the decision clearly. Naming a limitation you chose, and explaining exactly what it would take to remove it, reads as more senior than avoiding the topic.

**Interview-ready framing:** *"I authenticated the automated Lambda to GCP using a service account key in Secrets Manager rather than Workload Identity Federation — a deliberate simpler-first choice, with the trade-off (a long-lived static credential vs. WIF's short-lived tokens) named explicitly rather than left implicit. Interestingly, Google's own default policy on newer projects blocks key creation via the CLI specifically to push people toward WIF — I confirmed that was genuinely locked rather than something I was missing, worked around it through the console UI instead, and I've got a clear next step already scoped if I want to remove the static credential later."*

---

*(Next candidate for this log: Phase 5's SQL analysis — likely an entry on handling the growth-vs-seasonality confound in usage_events, flagged back in the Phase 1 addendum but not yet actually solved in a query.)*
