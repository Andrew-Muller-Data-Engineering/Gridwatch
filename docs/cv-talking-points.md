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

*(Next candidate for this log: extending the same boto3-deploy pattern to the Step Functions state machine and EventBridge schedule — likely another entry on "IAM roles for cross-service invocation," since Step Functions needs its own role scoped to just `lambda:InvokeFunction` on this one function.)*
