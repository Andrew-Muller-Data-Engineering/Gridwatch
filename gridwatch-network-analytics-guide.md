# GridWatch: UK Network Analytics — Personal Data Engineering Project

*(A working name — swap it out anywhere with a find-and-replace if you land on something better. "LoadSight" and "CircuitScope" are two other options in the same vein if you want alternatives.)*

A complete, self-contained build guide: environment setup through to a finished business case. Everything you need is in this one document.

**The concept:** GridWatch is a mock B2B (business-to-business — selling to companies, not individual consumers) SaaS (Software as a Service — a subscription-based software product) product sold to DNOs (Distribution Network Operators — the companies that run the local electricity network in a region) and specifically their asset planning and network operations teams. It gives them a live dashboard of network loading across their region, built from real grid data, with alerts when a substation or feeder looks like it's trending toward stress. Your "customers" are operations teams (accounts), your "users" are the engineers who log in and use it day to day.

**The business problem:** Do the accounts responsible for the highest-stress network regions actually engage with the product — or are the regions that most need proactive monitoring also the ones at highest risk of the customer not renewing? If there's a gap, what would you recommend to close it?

This mirrors real T&D-sector data work closely: you'll be handling genuine transmission and distribution data, building the kind of platform that a company selling into DNOs (Distribution Network Operators) or National Energy System Operator-adjacent services might actually build.

**A note on data granularity (accounts vs. properties):** it's easy to assume GridWatch should be working with data at the level of individual households/properties, since that's the scale a DNO's network ultimately serves (millions of premises) — and that's the right instinct if you're used to energy *retail* (supplier) data, where billing genuinely happens per property. Network operators work differently: they consume and publish data aggregated at substation/feeder or regional level (DNOs' own published smart meter datasets are explicitly aggregated — e.g. National Grid Electricity Distribution's "Aggregated Smart Meter Data – Secondary Substation" — with raw household-level access requiring a formal, Ofgem-governed Data Privacy Plan, not the default). GridWatch's own customers (the `accounts` table) are DNO ops teams — a few hundred at most, not millions — while the real-world property scale those teams are responsible for shows up as a `properties_served` field on each account instead. See the Phase 1 addendum below for how this plays out in the actual data.

---

## Skills this demonstrates (→ CV mapping)

| Area | What you'll actually do | Example CV bullet |
|---|---|---|
| Environment & tooling | Set up AWS and GCP from scratch, IDE-integrated | "Independently provisioned and configured a multi-cloud (AWS + GCP) development environment" |
| Event-driven ingestion | Lambda + Step Functions polling real grid APIs | "Built a serverless ingestion pipeline using Lambda and Step Functions to poll external transmission/distribution data sources on a schedule" |
| ETL / transformation | Cost-aware Glue jobs, partitioned Parquet | "Designed a cost-aware ETL layer using AWS Glue to clean and partition network data into a curated S3 zone" |
| Data warehousing | BigQuery star schema | "Modeled a star schema in BigQuery to support analytical querying over multi-source network and product usage data" |
| SQL analysis | Cohort/engagement analysis, joins across sources | "Wrote analytical SQL to identify the relationship between network load patterns and customer engagement/renewal risk" |
| Business communication | Stakeholder memo with a recommendation | "Translated network and usage data analysis into a business recommendation with estimated impact on customer retention" |
| Version control | GitHub, structured commit history | "Maintained a version-controlled, documented data engineering project from design through delivery" |

---

## Repository structure — and how to organize it locally in VS Code

One repo, not split by cloud provider — it's one project with one story. Here's the fuller structure, mirroring the pipeline stages so anyone browsing it (including you, six months from now) can see exactly how it fits together:

```
gridwatch/
├── .venv/                      (Python virtual environment — gitignored, one for the whole project)
├── .vscode/
│   └── settings.json           (pins the interpreter to .venv — see below)
├── .gitignore
├── .env                        (local secrets/config — gitignored, never committed)
├── README.md
├── requirements.txt
├── ingestion/
│   └── lambdas/
│       └── neso_ingest/
│           ├── handler.py
│           └── requirements.txt
├── transform/
│   └── glue_jobs/
│       └── clean_neso_data.py
├── infra/                      (Step Functions state machine definitions, Lambda deploy config/scripts, EventBridge schedule config)
├── warehouse/
│   ├── schema/
│   │   └── create_tables.sql
│   └── queries/
│       ├── engagement_vs_stress.sql
│       └── churn_risk.sql
├── mock_data/
│   ├── generate_accounts.py
│   ├── generate_usage_events.py
│   └── output/                 (generated CSVs — gitignored, regenerable any time)
├── notebooks/                  (exploratory analysis, BigQuery notebooks)
├── docs/
│   ├── architecture.md
│   └── business_case.md
└── tests/                      (add once you have logic worth testing)
```

**The reasoning, briefly:**
- **Folders mirror the architecture**, not the tools — `ingestion/`, `transform/`, `warehouse/` map directly to the pipeline diagram from earlier, so the repo's structure tells the same story as your CV bullets.
- **Each Lambda gets its own subfolder** with its own `requirements.txt` — AWS deploys each function as an isolated package, so keeping them separate from the start avoids a painful untangling later.
- **`infra/` treats your Step Functions definitions as code**, version-controlled alongside everything else — a small detail, but it signals infrastructure-as-code thinking, which is worth having on a CV project.
- **One shared `.venv/` at the root** is enough for a project this size — no need for a separate environment per Lambda locally (you'll only need isolated dependency lists when you actually package a Lambda for deployment).
- **`mock_data/output/` is gitignored** — generated data doesn't need to live in Git since the scripts can regenerate it any time; committing multi-thousand-row CSVs just bloats the repo's history.

**Important — the folder must be named exactly `mock_data` (underscore, no space).** Every command later in this guide (`python mock_data/generate_data.py`, `from regions import REGIONS`, `mock_data/output/...`) is a literal path. A folder named `mock data` (with a space) will make every one of those commands fail with a "file not found" style error, since as far as the terminal is concerned that's a completely different path. If you create folders by hand in Finder/File Explorer rather than copy-pasting, double check this one specifically.

**Working in VS Code:** open the `gridwatch` folder itself as your workspace (File → Open Folder), not any subfolder — this is what makes Source Control, the Python interpreter, and the file explorer all work correctly across the whole project at once.

**One nice touch — pin the interpreter for the project.** Create `.vscode/settings.json` with:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```
This means the correct virtual environment is selected automatically every time you (or anyone else) opens the project — small, but it's the kind of detail that makes a repo look properly maintained.

---

---

## A quick note on where things run

You'll see code blocks and commands throughout this guide. Since this is all new, every one is labelled with exactly where it goes:

- 🖥️ **Terminal** — a plain black/white text window on your PC where you type commands and press Enter. To open one: **Windows** — press the Windows key, type `powershell`, press Enter. **Mac** — press Cmd+Space, type `terminal`, press Enter. You can also open one inside VS Code itself: top menu → **Terminal** → **New Terminal**.
- 📝 **A file** — code that goes *inside* a file in your project (like a `.py` script). This doesn't do anything by itself the moment you write it — it only runs when you separately tell the terminal to run that file. Each label tells you the exact filename.
- 🌐 **Browser** — a normal website you click through (the AWS Console, Google Cloud Console, GitHub.com)
- 💻 **App** — a desktop application window (GitHub Desktop, or VS Code's own menus rather than its terminal)

If a label ever seems to contradict a step above it, the label wins — treat these as the source of truth for "where do I actually do this."

---

# Part 1 — Environment Setup

Do this section once, in order. If you've already done a step, skip it.

## 1.0 — Python itself, and why virtual environments matter

**Why this step exists:** every Python project needs its own isolated set of installed packages (libraries like `pandas`). Without isolation, one project's dependencies can quietly break another's — if GridWatch needs one version of a library and some other script on your PC needs a different, incompatible version, installing both directly onto your system creates a conflict neither project can recover from cleanly. A **virtual environment** (shortened to "venv") is a self-contained folder holding its own private copy of Python and its own installed packages, completely separate from anything else on your machine. Every time this guide says "activate your virtual environment," it means: tell Python to use that private folder instead of your system-wide install for this terminal session.

**Check Python is installed:**
🖥️ **Terminal:**
```
python --version
```
(On some Mac setups, try `python3 --version` instead if the first one says "command not found.") You want to see `Python 3.10` or newer printed back. If you see an error instead, go to python.org, download the installer, run it with default options, then come back.

**Create the virtual environment — once, inside your `gridwatch` project folder.** First, make sure your terminal is actually *inside* that folder:
🖥️ **Terminal:**
```
cd path/to/gridwatch
```
(replace `path/to/gridwatch` with wherever you actually saved it — e.g. `cd Documents/Projects/gridwatch`)

Then create the environment:
🖥️ **Terminal:**
```
python -m venv .venv
```
Nothing visibly happens for a few seconds — that's normal, it's just copying files. Afterwards, a new `.venv` folder appears inside `gridwatch`. That's your private environment; your `.gitignore` from Section 1.4 already excludes it from Git, since it's just installed packages, not code you wrote.

**Activate it — every time you open a fresh terminal to work on this project** (it does not stay active permanently, only for the current terminal window):
🖥️ **Terminal:**
- **Windows:** `.venv\Scripts\activate`
- **Mac:** `source .venv/bin/activate`

You'll know it worked because your terminal prompt now shows `(.venv)` at the very start of the line, before your normal prompt text.

**Why this matters in practice:** once activated, `pip install` and `python` commands use the private copy inside `.venv`, not your system-wide Python. If any command later in this guide throws a "module not found" error, the very first thing to check is whether you forgot to activate — look for that `(.venv)` prefix before troubleshooting anything else.

## 1.1 — AWS account and IAM setup

**Create your AWS account.** Go to aws.amazon.com and sign up with an email address. You'll be asked for a payment card — this is separate from your Google Cloud one, and AWS won't actually charge it as long as you stay within the Always Free limits (covered in Part 2 below). Skip this step if you already have an account.

**Secure the root account with MFA.** In the console, search "IAM" (Identity and Access Management — AWS's system for controlling who or what can access which resources) → Dashboard. You'll see a security recommendation to add multi-factor authentication to your root user — do this immediately. The root account has completely unrestricted access, so the rule is: use it only for account-level tasks like this, never for day-to-day work.

**Create an IAM user for daily work.** Go to IAM → Users → Create user. Give it a sensible name (your own name is fine), enable console access with a password, and for permissions attach "AdministratorAccess" — the simplest option while you're learning. You can tighten this to a scoped policy later once you know exactly which services you're using.

**Generate programmatic access keys.** Still on that IAM user, go to Security credentials → Access keys → Create access key → choose "Command Line Interface (CLI)" as the use case. You'll be shown an Access Key ID and a Secret Access Key — copy both immediately, the secret is only ever shown once.

**Install the AWS CLI** (Command Line Interface — lets you control AWS by typing commands instead of clicking through the console). Download it from AWS's CLI installation page for your operating system. Once installed, confirm it worked:
🖥️ **Terminal:**
```
aws --version
```

**Configure the CLI with your IAM user.**
🖥️ **Terminal:**
```
aws configure
```
It will prompt you one line at a time — paste in your Access Key ID, then your Secret Access Key, then type `eu-west-2` for region, then `json` for output format.

**Set a billing alarm.** In the Billing console → Budgets → Create budget. Set a small monthly threshold — £2 is a sensible trip-wire — with an email alert attached. This is your safety net for the whole project.

**Verify everything works.**
🖥️ **Terminal:**
```
aws sts get-caller-identity
```
It should return your IAM user's account ID and ARN (Amazon Resource Name — a unique ID AWS gives every resource you create), confirming the CLI is correctly authenticated against your new user. **Keep this account ID handy — Phase 2 needs it.**

## 1.2 — VS Code configured for AWS

**Install the AWS Toolkit extension.** In VS Code's Extensions panel (Ctrl/Cmd+Shift+X), search "AWS Toolkit" (published by Amazon Web Services) and install it.

**Connect it to your credentials.** Click the AWS icon that appears in the left sidebar. Because you already ran `aws configure`, the Toolkit detects your credentials automatically from `~/.aws/credentials` — select that profile when prompted.

**Browse your resources directly in the editor.** The AWS Explorer panel now lets you browse S3 buckets, Lambda functions, and Step Functions state machines without switching to the browser — genuinely useful once Phase 2 (ingestion) is underway.

**Install the Python extension.** Search "Python" (by Microsoft) in Extensions and install it. Then use Ctrl/Cmd+Shift+P → "Python: Select Interpreter" and point it at the virtual environment you'll create for this project.

## 1.3 — VS Code configured for BigQuery

**Install the Google Cloud CLI.** Download `gcloud` from Google Cloud's SDK install page, then:
🖥️ **Terminal:**
```
gcloud init
```
Sign in with the same Google account your BigQuery project lives on when prompted.

**Install the Jupyter extension.** In Extensions, search "Jupyter" (by Microsoft) and install it — it's a required dependency for the BigQuery features below.

**Install the Google Cloud Code extension.** Search "Google Cloud Code" in Extensions and install it. This adds a Google Cloud icon to your sidebar.

**Sign in and set your project.** Click the Google Cloud Code icon → "Login to Google Cloud." Then open the extension's settings and set "Cloud Code: Project" to your BigQuery project.

**Browse and query your data.** Open the BigQuery Notebooks section in the Google Cloud Code panel to browse datasets and tables directly, or open a BigQuery Notebook to write and run SQL against your data without leaving the editor.

## 1.4 — GitHub Desktop, connected to VS Code

## 1.4 — Git, GitHub, and VS Code, connected together (click-by-click)

Quick concept first: **Git** tracks changes to your files on your own PC — every "commit" saves a snapshot you can return to later. **GitHub** is a website that hosts a copy of that history online. **GitHub Desktop** and **VS Code's Source Control panel** are two different button-and-menu ways of doing the same Git actions on the same project — you don't need both, but it's useful to know both exist.

### Step 1: Create your GitHub account
1. Open your web browser and go to `github.com`
2. In the top-right corner, click **Sign up**
3. Enter your email address and click **Continue**
4. Create a password (GitHub shows the requirements as you type) and click **Continue**
5. Choose a username — this becomes part of your project's public link, so something professional-looking is worth it — and click **Continue**
6. Complete the short verification puzzle if one appears
7. GitHub emails you a verification code — check your inbox, enter the code on the page, and click **Continue**
8. You'll land on a short "what will you use GitHub for" questionnaire — answer it or click **Skip personalization**, and you'll arrive at your new account's homepage

### Step 2: Install Git itself
This is the actual engine that both GitHub Desktop and VS Code rely on underneath.
1. Go to `git-scm.com` in your browser
2. Click the **Download for Windows** (or **macOS**) button — the site usually auto-detects your operating system and shows the right one
3. The file downloads to your Downloads folder — open that folder and double-click the installer
4. **Windows only:** you may see "Do you want to allow this app to make changes to your device?" — click **Yes**
5. Click **Next** through every screen of the installer — the default option on each screen is correct, you don't need to change anything
6. On the final screen, click **Install**, wait for the progress bar to finish, then click **Finish**
7. Now open a terminal to check it worked:
   - **Windows:** press the Windows key, type `powershell`, press Enter
   - **Mac:** press Cmd+Space, type `terminal`, press Enter
8. In the terminal window, type `git --version` and press Enter — you should see something like `git version 2.44.0`. That confirms it's installed.

### Step 3: Tell Git who you are
Still in that same terminal window:
1. Type exactly (with your real name inside the quotes): `git config --global user.name "Your Name"` then press Enter
2. Type (with the same email you used for GitHub): `git config --global user.email "your-email@example.com"` then press Enter
3. Neither command shows any output when it works — no error message means it succeeded

### Step 4: Install and sign in to GitHub Desktop
1. Go to `desktop.github.com` in your browser
2. Click **Download for Windows** (or macOS)
3. Open the downloaded file and click through the installer — default options throughout
4. Once GitHub Desktop opens, click **Sign in to GitHub.com**
5. Your browser opens and asks you to authorize the app — click **Authorize desktop**
6. Switch back to the GitHub Desktop app window — it now shows you as signed in

### Step 5: Create your project repository
1. In GitHub Desktop, click **File** (top-left menu bar) → **New Repository...**
2. In the **Name** field, type `gridwatch`
3. Next to **Local Path**, click **Choose...** and pick a sensible folder on your PC (e.g. a "Projects" folder inside Documents)
4. Tick the checkbox **Initialize this repository with a README**
5. Leave "Git ignore" and "Licence" both set to **None** for now
6. Click **Create Repository**

GitHub Desktop now shows your new repo with one file (`README.md`) already inside it.

### Step 6: Add the folder structure
1. Open the `gridwatch` folder you just created, in File Explorer (Windows) or Finder (Mac)
2. Right-click inside the folder → **New** → **Folder** (Windows) or right-click → **New Folder** (Mac)
3. Create each of these, one at a time: `ingestion`, `transform`, `infra`, `warehouse`, `mock_data`, `notebooks`, `docs`, `tests` (see the **Repository structure** section above for what each is for) — note the underscore in `mock_data`, not a space
4. Worth knowing: Git only tracks a folder once it has at least one file inside it, so these will look "empty" to Git for now — that's fine, nothing to fix yet

### Step 7: Add your `.gitignore` file — do this before adding any real project files
1. In the same `gridwatch` folder, create a new file named exactly `.gitignore` — including the leading dot, and no file extension after it (some systems hide extensions by default, so double-check it isn't secretly saved as `.gitignore.txt`)
2. Right-click it → **Open with** → any plain text editor (Notepad on Windows, TextEdit on Mac)
3. Paste in exactly:
```
.venv/
__pycache__/
*.pyc
.env
*credentials*.json
*.pem
```
4. Save the file (Ctrl/Cmd+S) and close it

This stops Python clutter *and*, critically, stops you ever accidentally uploading AWS keys or GCP credential files to a public repository — worth keeping as a habit beyond this project too.

### Step 8: Make your first commit
1. Switch to GitHub Desktop — it now lists your new folders and `.gitignore` file under "Changes" on the left
2. In the box at the bottom-left, type a short summary, e.g. `Initial project setup`
3. Click the blue **Commit to main** button

### Step 9: Publish your repository to GitHub
1. Click **Publish repository** at the top of the GitHub Desktop window
2. In the dialog: untick **Keep this code private** if you want it public and CV-linkable (recommended) — or leave it ticked to keep it private for now
3. Click **Publish Repository**
4. Check it worked by visiting `github.com/your-username/gridwatch` in your browser — you should see your files there

### Step 10: Open the project in VS Code
1. Open VS Code
2. Click **File** (top-left) → **Open Folder...**
3. Browse to your `gridwatch` folder, select it, then click **Select Folder** (Windows) or **Open** (Mac)
4. If asked "Do you trust the authors of the files in this folder?", click **Yes, I trust the authors**
5. Look at the icons down the left sidebar — click the one that looks like a small branching line (this is **Source Control**). A number badge appears on it whenever you have unsaved changes.

### Step 11: Link GitHub Desktop and VS Code together
1. In GitHub Desktop, click **File** → **Options...** (Windows) or **GitHub Desktop** → **Settings...** (Mac, top-left of the screen, not inside the app window)
2. Click the **Integrations** tab
3. In the **External editor** dropdown, choose **Visual Studio Code**
4. Close the settings window

From now on, in GitHub Desktop, the **Repository** menu → **Open in Visual Studio Code** always opens this project correctly.

### Step 12: Making changes day-to-day — now with branches

**Why branch instead of committing straight to `main`:** `main` is meant to always be in a working state — the version you'd show someone, or come back to after a break. A **branch** is a parallel, independent copy of the project where you can make changes, break things, experiment, and commit as many half-finished attempts as you like, without touching `main` at all. Once the change is finished and working, you **merge** it back into `main` in one clean step. This matters more as the project grows: from Phase 2 onward you're touching AWS resources, and a broken half-written Lambda sitting on `main` is a worse place to be than the same broken code sitting safely on its own branch until it's ready.

**The pattern for every change, from now on:**
1. Create a branch, named for what you're about to do (e.g. `phase1-mock-data`, `fix-mock-data-folder-name`)
2. Make your changes and commit them to that branch — as many small commits as you like
3. Push the branch to GitHub
4. Merge it back into `main` once it's finished and working (either directly, or via a **pull request** — see the **What** section below)
5. Delete the branch — its commits live on inside `main`'s history once merged, so deleting the branch itself loses nothing

**How — using GitHub Desktop:**
1. Open GitHub Desktop, with the GridWatch repo selected
2. Click the **Current branch** dropdown near the top (it currently says "main")
3. Click **New branch**
4. Type a name (lowercase, hyphens instead of spaces, e.g. `phase1-mock-data`) and click **Create branch**
5. GitHub Desktop automatically switches you onto it — the dropdown now shows your new branch name instead of "main"
6. Work as normal: edit files in VS Code, save them, then back in GitHub Desktop write a commit message and click **Commit to `<branch-name>`**
7. Click **Publish branch** (first time) or **Push origin** (after that) to send it to GitHub
8. When the change is finished and working: click the **Current branch** dropdown → switch to `main` → click **Branch** (top menu) → **Merge into current branch...** → pick your feature branch → **Merge**
9. Push `main` again (**Push origin**) to send the merged result to GitHub
10. Optional cleanup: **Branch** (top menu) → **Delete...** → pick the now-merged branch → confirm

**How — using VS Code instead:**
1. Click the branch name in the bottom-left corner of the VS Code window (it shows "main")
2. Choose **Create new branch...** from the list that appears
3. Type a name and press Enter — VS Code switches you onto it automatically (the bottom-left corner updates to show the new name)
4. Work, save, and commit through the Source Control panel exactly as before: stage changes with the **+**, type a message, click **✓ Commit**
5. Click **Sync Changes** (or **Publish Branch** the first time) to push it
6. To merge back: click the branch name bottom-left → switch to `main` → open the Source Control panel → click the **...** menu → **Branch** → **Merge Branch...** → pick your feature branch
7. Push `main` (**Sync Changes**)
8. Optional cleanup: click the branch name bottom-left → **Delete branch...**

**On pull requests (optional, but worth knowing):** instead of merging locally (Steps 8-9 above), you can push the branch and open a **pull request** on github.com instead — same end result (the branch merges into `main`), but it gives you a page showing exactly what changed before it merges. It's the standard way collaborative teams review code, and "opened and merged pull requests" is a genuinely relevant Git skill to have practiced, even solo.

**When it's fine to skip branching:** tiny, low-risk edits — fixing a typo in the README, tweaking a comment — are fine committed straight to `main`. Anything that touches actual pipeline code, or that you're not fully sure works yet, goes on a branch.

Use whichever app (GitHub Desktop or VS Code) feels more natural at the time for any given step — they update the same repository either way.

### What — branching reference

- **Branch** — a parallel, independent line of commits, starting from wherever `main` was when you created it. Changes on a branch don't affect `main` until you merge.
- **Merge** — folding one branch's commits into another (typically a feature branch back into `main`).
- **Pull request (PR)** — a GitHub page proposing that one branch be merged into another, showing the diff and allowing comments, before the merge actually happens. Standard practice on real teams; optional but good practice solo.
- **Feature branch** — informal name for a branch created for one specific piece of work, deleted once merged.
- **Checkout / switch** — moving your working copy of the files to match a different branch's version.

---

# Part 2 — Cost reality check

Most of this stack is free indefinitely. One piece isn't quite, so plan around it:

- **Lambda** — 1 million requests and 400,000 GB-seconds of compute per month, always free, never expires.
- **Step Functions** — 4,000 free state transitions per month, available indefinitely (not just for 12 months).
- **Glue Data Catalog** (schema/metadata storage) — 1 million objects and 1 million accesses per month, always free.
- **Glue crawlers/ETL jobs** (actual compute) — **not** part of the always-free tier, billed per DPU-hour (DPU = Data Processing Unit, AWS Glue's unit of compute power). This is the one gap — addressed directly in Phase 3 below.
- **S3** — 5 GB storage, 20,000 GET and 2,000 PUT requests per month, always free on a new account.
- **BigQuery** — 1 TiB of query processing and 10 GB of storage per month, free forever.

For the Glue gap: use the smallest possible job configuration (covered in Phase 3), run infrequently, and treat your remaining £226 Google Cloud credit and the AWS billing alarm as your safety net — the realistic cost is pennies, not pounds.

---

# Part 3 — Build the project

## Phase 1 — Mock customer data (Python)

### Why

- **Why this phase exists at all:** in a real company, GridWatch's customer and usage data would already exist in a production database — it's the one thing here that's genuinely proprietary, so nobody publishes it for you to download. You have to invent it, but invent it *deliberately*, so it behaves like real data would: messy, varied, with a genuine pattern hiding in it for Phase 5 to find, rather than something perfectly clean and obviously fake.
- **Why resolve the join key before writing any data:** later, you'll want to ask questions like "do accounts in high-stress network regions engage less with the product?" That only works if your mock accounts and the real NESO data agree on what a "region" is. NESO's Carbon Intensity API already defines a fixed, official list of 14 GB regions with stable numeric IDs — reusing that exact list, rather than inventing your own region names, is what makes a later SQL join actually work instead of silently returning nothing.
- **Why `faker` and `pandas` specifically:** `faker` generates realistic fake data (names, companies, dates) so you're not hand-typing company names yourself. `pandas` is the standard Python tool for tabular data — you'll use it again in Phase 5, so it's worth the familiarity now, on data you already understand.
- **Why one file, built up in pieces, rather than several small ones:** a Python file runs top to bottom when executed, and a function has to be *defined* before it's *called*. Keeping the three table-generating functions and the code that calls them in one file makes that ordering visible and easy to follow while you're still learning the pattern — you can split it into multiple files later once it feels natural.
- **Why the specific design choices in the `accounts` table:** an 18-month signup window (not literally today) ensures every account already has some usage history for Phase 5 to analyze. A 15% baseline churn rate gives you a believable mix of active and lost customers. Weighting toward the cheapest tier (50% Basic) mirrors how real SaaS customer bases are actually shaped — most customers on the entry plan, fewer on the expensive one.
- **Why `random.gauss` for the noise:** real usage is never a perfectly flat number every week. Adding Gaussian (bell-curve) noise around an average makes the data look like genuine human behaviour rather than a robotic, obviously-generated pattern.
- **Why wrap everything in `pandas.DataFrame(...).to_csv(...)` instead of writing the CSV by hand:** the three functions return plain Python lists of dictionaries — accurate, but not something you can easily inspect or save correctly. `pandas` handles the fiddly formatting (commas inside company names, quoting, etc.) that's easy to get wrong doing it manually.
- **Why verify before moving on, rather than trusting it worked:** catching a problem now — while only one script is involved — is far easier than debugging it three phases later, once it's tangled up with real AWS data too.

### How

**1. Install the libraries.**
🖥️ **Terminal** (check your prompt shows `(.venv)` from Section 1.0 first):
```
pip install faker pandas
```

**2. Create `mock_data/regions.py`.** 📝 In VS Code: right-click the `mock_data` folder → **New File** → type `regions.py` → Enter. Paste in, then save (Ctrl/Cmd+S):
```python
REGIONS = [
    {"region_id": 1,  "region_name": "North Scotland"},
    {"region_id": 2,  "region_name": "South Scotland"},
    {"region_id": 3,  "region_name": "North West England"},
    {"region_id": 4,  "region_name": "North East England"},
    {"region_id": 5,  "region_name": "South Yorkshire"},
    {"region_id": 6,  "region_name": "North Wales, Merseyside and Cheshire"},
    {"region_id": 7,  "region_name": "South Wales"},
    {"region_id": 8,  "region_name": "West Midlands"},
    {"region_id": 9,  "region_name": "East Midlands"},
    {"region_id": 10, "region_name": "East England"},
    {"region_id": 11, "region_name": "South West England"},
    {"region_id": 12, "region_name": "South England"},
    {"region_id": 13, "region_name": "London"},
    {"region_id": 14, "region_name": "South East England"},
]
```
That file is done — you won't touch it again in this phase, only import from it. (It's since grown a second block, `REGION_PROFILE` and `CONSTRAINT_PRONE_REGIONS` — see the addendum at the end of this phase.)

**3. Create `mock_data/generate_data.py`.** 📝 Right-click the `mock_data` folder → **New File** → type `generate_data.py` → Enter. Steps 4-7 below all get typed into *this one file*, top to bottom, in order — you run the whole thing once, at Step 8.

**4. Add the accounts section.**
📝 **File — `mock_data/generate_data.py`:**
```python
import random
from faker import Faker
from datetime import timedelta
from regions import REGIONS

fake = Faker("en_GB")
random.seed(42)  # remove once you're happy with the shape of the data — see the What section below

TIERS = ["Basic", "Pro", "Enterprise"]
TIER_WEIGHTS = [0.5, 0.35, 0.15]

def generate_accounts(n=250):
    accounts = []
    for i in range(n):
        region = random.choice(REGIONS)
        start = fake.date_between(start_date="-18m", end_date="-1m")
        renewal = start + timedelta(days=365)
        churned = random.random() < 0.15
        churn_date = fake.date_between(start_date=start, end_date="today") if churned else None
        accounts.append({
            "account_id": i + 1,
            "account_name": fake.company(),
            "region_id": region["region_id"],
            "region_name": region["region_name"],
            "contract_tier": random.choices(TIERS, weights=TIER_WEIGHTS)[0],
            "contract_start_date": start,
            "renewal_date": renewal,
            "churn_date": churn_date,
        })
    return accounts
```

**5. Directly underneath, add the users section.**
📝 **File — `mock_data/generate_data.py` (append below what you just added):**
```python
ROLES = ["Network Engineer", "Asset Planner", "Operations Manager", "Data Analyst"]

def generate_users(accounts):
    users, user_id = [], 1
    for account in accounts:
        for _ in range(random.randint(1, 4)):
            users.append({
                "user_id": user_id,
                "account_id": account["account_id"],
                "role": random.choice(ROLES),
                "signup_date": account["contract_start_date"],
            })
            user_id += 1
    return users
```

**6. Underneath that, add the usage events section.**
📝 **File — `mock_data/generate_data.py` (append below what you just added):**
```python
EVENT_TYPES = ["login", "view_dashboard", "view_alert", "acknowledge_alert", "generate_report"]
EVENT_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]
LOW_ENGAGEMENT_REGIONS = {1, 2, 6, 7}  # North Scotland, South Scotland, N Wales/Mersey/Cheshire, South Wales

def generate_usage_events(users, accounts_by_id):
    events = []
    for user in users:
        account = accounts_by_id[user["account_id"]]
        base_events_per_week = 6
        if account["region_id"] in LOW_ENGAGEMENT_REGIONS:
            base_events_per_week *= 0.6
        for week in range(52):
            n_events = max(0, int(random.gauss(base_events_per_week, 2)))
            for _ in range(n_events):
                event_date = fake.date_between(start_date=account["contract_start_date"], end_date="today")
                events.append({
                    "user_id": user["user_id"],
                    "event_timestamp": event_date,
                    "event_type": random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0],
                })
    return events
```

**7. Right at the very bottom, add the part that runs everything.**
📝 **File — `mock_data/generate_data.py` (append at the very end):**
```python
import pandas as pd

accounts = generate_accounts(250)
users = generate_users(accounts)
accounts_by_id = {a["account_id"]: a for a in accounts}
events = generate_usage_events(users, accounts_by_id)

pd.DataFrame(accounts).to_csv("mock_data/output/accounts.csv", index=False)
pd.DataFrame(users).to_csv("mock_data/output/users.csv", index=False)
pd.DataFrame(events).to_csv("mock_data/output/usage_events.csv", index=False)
print(f"Generated {len(accounts)} accounts, {len(users)} users, {len(events)} events")
```
Save the file (Ctrl/Cmd+S). It should now contain all four blocks from Steps 4-7, stacked top to bottom, in that order.

**8. Create the output folder, then run the script.** In File Explorer/Finder (or right-click `mock_data` in VS Code → **New Folder**), create an empty folder named `output` inside `mock_data`.

🖥️ **Terminal** (same terminal, `.venv` still activated, still inside the `gridwatch` folder):
```
python mock_data/generate_data.py
```
You should see a line like `Generated 250 accounts, 612 users, 71304 events` — that confirms it worked.

**9. Verify.** Open `mock_data/output/accounts.csv` (click it in VS Code's file explorer to preview it) and check `region_id` spreads across all 14 values, not clustered in two or three. Spot-check `usage_events.csv` shows visibly fewer rows for users in region 1, 2, 6, or 7. If everything looks near-identical, turn the noise/bias numbers up (see the **What** section below for exactly which ones).

> **Note — the version above is the original, first-pass build.** It was superseded shortly after by the realism pass in the **Addendum** below (region-weighted accounts, `properties_served`, `CONSTRAINT_PRONE_REGIONS`, seasonality, financial-year-nudged signups). The **What** section immediately below documents the original version's syntax for learning purposes; the addendum documents what changed and why. The addendum's version is what's actually in the repo.

### What — argument and concept reference

**`regions.py`:** this is a *list* (square brackets `[ ]`) containing *dictionaries* (each `{ }` entry) — a dictionary is a set of labelled values, like `region_id: 1` paired with `region_name: "North Scotland"`. This shape — a list of dictionaries — is reused throughout `generate_data.py`, and it's exactly what pandas expects when converting to a table in Step 7.

**Accounts function:**
- `Faker("en_GB")` — `Faker` is a class from the faker library; calling it creates a "faker object" you ask to generate fake data from. `"en_GB"` is the locale argument — British-style company names/addresses rather than the American default.
- `random.seed(42)` — one argument, a starting number for the random generator. Any fixed number works; what matters is that the *same* seed always reproduces the *same* "random" data, useful while tuning. Delete this line once you're happy with the results, so future runs are genuinely fresh.
- `random.choice(REGIONS)` — one argument, a list; returns a single random item from it.
- `fake.date_between(start_date="-18m", end_date="-1m")` — `start_date`/`end_date` are keyword arguments; Faker accepts relative strings like `"-18m"` (18 months ago) instead of you calculating an actual date. (This call turned out not to be reliable in practice — see the Phase 1 troubleshooting note and the addendum's `random_date_between` replacement.)
- `timedelta(days=365)` — a keyword argument specifying a length of time; adding it to a date gives a new date that many days later.
- `random.random()` — no arguments; returns a decimal between 0 and 1. `< 0.15` turns that into "true 15% of the time."
- `fake.date_between(...) if churned else None` — not a function argument, a *conditional expression*: "do the first part if `churned` is true, otherwise use `None`."
- `random.choices(TIERS, weights=TIER_WEIGHTS)[0]` — note the *s*: `choices` (plural) differs from `choice` (singular) above. First argument is the list to pick from; `weights=` is optional, for uneven odds. Always returns a *list*, hence `[0]` to pull out the single result.
- `def generate_accounts(n=250):` — `n=250` is a *default argument*: `generate_accounts()` uses 250 automatically; `generate_accounts(500)` overrides it.

**Users function:**
- `random.randint(1, 4)` — two arguments, min and max, *both inclusive* — can return 1, 2, 3, or 4.
- `range(random.randint(1, 4))` — `range()` with one argument counts 0 up to (not including) that number, so this loop runs 1-4 times.
- `account["contract_start_date"]` — square brackets after a dictionary retrieve one value by key name.

**Usage events function:**
- `random.gauss(base_events_per_week, 2)` — two arguments: mean (average) and standard deviation (spread around it). `2` here means most weeks land within roughly ±2 of the average.
- `max(0, int(random.gauss(...)))` — `max()` returns whichever argument is largest; here it's a safety net stopping a rare negative `gauss` result from becoming a negative number of events.
- `int(...)` — one argument, converts a decimal (e.g. `5.7`) to a whole number.
- `range(52)` — counts 0 to 51, matching 52 weeks in a year.
- `{1, 2, 6, 7}` — curly braces *without* colons make this a *set*, not a dictionary — built for fast "is this value in here?" checks, exactly what `in LOW_ENGAGEMENT_REGIONS` does.
- `base_events_per_week *= 0.6` — shorthand for `base_events_per_week = base_events_per_week * 0.6`.

**Tie-together section:**
- `{a["account_id"]: a for a in accounts}` — a *dict comprehension*: "for every account in `accounts`, create an entry keyed by its ID, pointing at the whole record" — lets later code look up any account instantly by ID instead of searching the whole list.
- `pd.DataFrame(accounts)` — one argument, a list of dictionaries; converts it to a table, with dictionary keys becoming column names.
- `.to_csv("mock_data/output/accounts.csv", index=False)` — first argument is the file path; `index=False` (keyword) stops pandas adding its own extra numbering column.
- `f"Generated {len(accounts)}..."` — the `f` prefix makes this an *f-string*, letting a variable drop straight into text via `{ }`. `len(accounts)` takes one argument (a list) and returns its item count.

**Definition of done (original):** three CSVs in `mock_data/output/`, covering a full year, `region_id` as a clean shared key ready to join against NESO data, and a genuine (if noisy) engagement gap between regions for Phase 5 to find.

### Troubleshooting note — Faker's relative date strings

The first real run of this script produced every single date (`contract_start_date`, `renewal_date`, `churn_date`, and every `usage_events.event_timestamp`) as the exact same day. The cause: `fake.date_between(start_date="-18m", end_date="-1m")` didn't reliably resolve to an 18-months-to-1-month-ago window in the installed Faker version — it collapsed to essentially "today" every time, and that then cascaded into the calls that depended on it. The fix, carried into the addendum below, was to stop relying on Faker's relative-string date parsing entirely and do the date math directly in Python (`random_date_between`) — more explicit, and not dependent on a specific library version's parsing behaviour.

### Addendum — making the mock data more realistic

After the first working version above, the generator was revisited to ground more of it in real regional data rather than arbitrary choices, prompted by wanting Phase 5's eventual findings to rest on defensible assumptions rather than synthetic guesses — and to correct a scale/domain mismatch (see the note near the top of this guide on `accounts` vs. `properties_served`).

**Why:**
- **Region-weighted accounts:** real DNO customer counts vary hugely by region — UK Power Networks (London/South East/East England) serves roughly 8 million customers combined; SSEN (North Scotland + Southern England) serves roughly 3.9 million combined, across a much larger, sparser territory. Picking accounts with `random.choice` (uniform across all 14 regions) ignored this entirely. `REGION_PROFILE` in `regions.py` now assigns each region a `population_weight` used to bias `random.choices`, so London/South East/East England get noticeably more accounts than North/South Scotland — not because Scotland is unimportant, but because there are genuinely fewer premises there for a regional ops team to be responsible for. (These weights are a defensible relative ordering, not an exact census — precise per-DNO figures for all 14 regions weren't readily available from a quick research pass.)
- **`properties_served`:** DNOs' real customers number in the millions, but those are the *properties on the network*, not GridWatch's B2B SaaS customers (the ops teams). Rather than inflating the account count to represent millions of end-consumers — which would misrepresent who GridWatch actually sells to — each account now carries a `properties_served` field: a realistic property count for that team's patch, scaled by the same region tier as the account placement.
- **`CONSTRAINT_PRONE_REGIONS` (North + South Scotland):** the original arbitrary 4-region "low engagement" set has been replaced with a real, current dynamic — Scotland generates more wind power than the transmission grid can currently export south, and GB-wide constraint (curtailment) payments hit roughly £1.8bn in 2025, up 20% on 2024, disproportionately in Scotland. This is checkable against real data once Phase 2's NESO ingestion is live, rather than being an assertion Phase 1 just makes up.
- **Winter-weighted usage events:** grid stress and demand both genuinely rise in winter (this is part of why NESO's own demand forecasting has a whole "Average Cold Spell" methodology, simulating thousands of synthetic weather winters). `SEASONAL_MULTIPLIER` biases the expected weekly event count higher in Nov–Feb and lower in Jun–Aug.
- **Financial-year-nudged signups:** DNOs operate on an April–March financial year under Ofgem's RIIO-ED2 price control (a fixed 5-year settlement, 2023–2028), so B2B software budget decisions plausibly cluster around that reset. `pull_toward_financial_year_start` nudges each account's `contract_start_date` partway toward the nearest 1 April, rather than leaving signups perfectly uniform across the window.

**How — the updated `mock_data/regions.py`** (replaces the Step 2 version above — `REGIONS` is unchanged, this is appended underneath it):
```python
# Rough, illustrative weighting for account distribution and account "size"
# (properties_served), grounded in real regional customer counts where
# available (UK Power Networks ~8m across London/South East/East England;
# SSEN ~3.9m across North Scotland + Southern England) and reasonable
# population-based tiers elsewhere.
REGION_PROFILE = {
    1:  {"population_weight": 1, "properties_range": (8, 60)},    # North Scotland
    2:  {"population_weight": 1, "properties_range": (8, 60)},    # South Scotland
    3:  {"population_weight": 2, "properties_range": (30, 150)},  # North West England
    4:  {"population_weight": 1, "properties_range": (10, 70)},   # North East England
    5:  {"population_weight": 2, "properties_range": (30, 150)},  # South Yorkshire
    6:  {"population_weight": 1, "properties_range": (10, 70)},   # North Wales, Merseyside and Cheshire
    7:  {"population_weight": 1, "properties_range": (10, 70)},   # South Wales
    8:  {"population_weight": 2, "properties_range": (30, 150)},  # West Midlands
    9:  {"population_weight": 2, "properties_range": (30, 150)},  # East Midlands
    10: {"population_weight": 3, "properties_range": (80, 400)},  # East England
    11: {"population_weight": 2, "properties_range": (30, 150)},  # South West England
    12: {"population_weight": 2, "properties_range": (30, 150)},  # South England
    13: {"population_weight": 3, "properties_range": (80, 400)},  # London
    14: {"population_weight": 3, "properties_range": (80, 400)},  # South East England
}

# Regions carrying the real, disproportionate share of GB's wind curtailment
# burden — used to bias product engagement lower in these regions.
CONSTRAINT_PRONE_REGIONS = {1, 2}
```

**How — the updated `mock_data/generate_data.py`** (replaces Steps 4-7 above in full):
```python
import random
from faker import Faker
from datetime import date, timedelta
from regions import REGIONS, REGION_PROFILE, CONSTRAINT_PRONE_REGIONS

fake = Faker("en_GB")
random.seed(42)

def random_date_between(start, end):
    """A random calendar date between two dates (inclusive). Uses the
    already-seeded `random` module directly instead of Faker's relative
    date-string shorthand — see the troubleshooting note above."""
    days_between = (end - start).days
    if days_between <= 0:
        return start
    return start + timedelta(days=random.randint(0, days_between))

def pull_toward_financial_year_start(d, earliest, latest, strength=0.35):
    """Nudges a date some fraction of the way toward the nearest 1 April
    (the UK utility financial year start), then clamps it back inside the
    allowed window."""
    candidates = [date(d.year - 1, 4, 1), date(d.year, 4, 1), date(d.year + 1, 4, 1)]
    nearest_april = min(candidates, key=lambda c: abs((c - d).days))
    pulled = d + timedelta(days=int((nearest_april - d).days * strength))
    return max(earliest, min(latest, pulled))

TIERS = ["Basic", "Pro", "Enterprise"]
TIER_WEIGHTS = [0.5, 0.35, 0.15]

def generate_accounts(n=450):
    accounts = []
    today = date.today()
    earliest_start = today - timedelta(days=18 * 30)
    latest_start = today - timedelta(days=30)
    region_weights = [REGION_PROFILE[r["region_id"]]["population_weight"] for r in REGIONS]
    for i in range(n):
        region = random.choices(REGIONS, weights=region_weights)[0]
        start = random_date_between(earliest_start, latest_start)
        start = pull_toward_financial_year_start(start, earliest_start, latest_start)
        renewal = start + timedelta(days=365)
        churned = random.random() < 0.15
        churn_date = random_date_between(start, today) if churned else None
        low_k, high_k = REGION_PROFILE[region["region_id"]]["properties_range"]
        properties_served = random.randint(low_k * 1000, high_k * 1000)
        accounts.append({
            "account_id": i + 1,
            "account_name": fake.company(),
            "region_id": region["region_id"],
            "region_name": region["region_name"],
            "contract_tier": random.choices(TIERS, weights=TIER_WEIGHTS)[0],
            "contract_start_date": start,
            "renewal_date": renewal,
            "churn_date": churn_date,
            "properties_served": properties_served,
        })
    return accounts

ROLES = ["Network Engineer", "Asset Planner", "Operations Manager", "Data Analyst"]

def generate_users(accounts):
    users, user_id = [], 1
    for account in accounts:
        for _ in range(random.randint(1, 4)):
            users.append({
                "user_id": user_id,
                "account_id": account["account_id"],
                "role": random.choice(ROLES),
                "signup_date": account["contract_start_date"],
            })
            user_id += 1
    return users

EVENT_TYPES = ["login", "view_dashboard", "view_alert", "acknowledge_alert", "generate_report"]
EVENT_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]

SEASONAL_MULTIPLIER = {
    1: 1.35, 2: 1.30, 3: 1.15, 4: 1.00, 5: 0.90, 6: 0.85,
    7: 0.80, 8: 0.80, 9: 0.90, 10: 1.05, 11: 1.25, 12: 1.35,
}

def generate_usage_events(users, accounts_by_id):
    events = []
    today = date.today()
    for user in users:
        account = accounts_by_id[user["account_id"]]
        base_events_per_week = 6
        if account["region_id"] in CONSTRAINT_PRONE_REGIONS:
            base_events_per_week *= 0.6
        week_start = account["contract_start_date"]
        while week_start <= today:
            expected = base_events_per_week * SEASONAL_MULTIPLIER[week_start.month]
            n_events = max(0, int(random.gauss(expected, 2)))
            for _ in range(n_events):
                event_date = week_start + timedelta(days=random.randint(0, 6))
                if event_date > today:
                    event_date = today
                events.append({
                    "user_id": user["user_id"],
                    "event_timestamp": event_date,
                    "event_type": random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0],
                })
            week_start += timedelta(days=7)
    return events

import pandas as pd

accounts = generate_accounts(450)
users = generate_users(accounts)
accounts_by_id = {a["account_id"]: a for a in accounts}
events = generate_usage_events(users, accounts_by_id)

pd.DataFrame(accounts).to_csv("mock_data/output/accounts.csv", index=False)
pd.DataFrame(users).to_csv("mock_data/output/users.csv", index=False)
pd.DataFrame(events).to_csv("mock_data/output/usage_events.csv", index=False)
print(f"Generated {len(accounts)} accounts, {len(users)} users, {len(events)} events")
```

**A data-quality nuance worth knowing about, not a bug:** if you group `usage_events` by raw calendar month, the winter-weighting doesn't visually jump out — Jun/Jul actually look busiest in a raw count. That's because the account base itself grows fast over the 18-month window (far more accounts exist by month 12 than by month 1), and that growth swamps the seasonal signal in a raw total. Normalize by the number of *active* accounts in each month (events ÷ active users that month) and the intended winter peak reappears clearly — events-per-active-user rises through autumn, peaks around Nov–Jan, and falls back over spring/summer. This is a genuinely realistic wrinkle (real SaaS usage data has exactly this "growth vs. seasonality" confound) and a legitimate thing to handle explicitly in the Phase 5 SQL — e.g. normalizing by active accounts, or comparing accounts of similar tenure — rather than something to fix away here.

**Also worth knowing:** the financial-year pull can produce a visibly "twin-peaked" `contract_start_date` distribution rather than one smooth bump around a single April — since the 18-month window spans two separate 1 April dates, dates roughly equidistant between them (around Aug–Nov) get pulled toward whichever April is nearer, thinning out that middle stretch more than a single-peak intuition would expect. This is a real, explainable consequence of the pull logic (not a bug), and arguably a *better* story than a single bump: two waves of signups, each shortly after a financial-year reset.

**What — new fields/concepts in the addendum:**
- `properties_served` (accounts.csv) — approximate real-world property count covered by that account's operational patch, scaled by the region's customer-density tier.
- `REGION_PROFILE` (regions.py) — per-region `population_weight` (biases account placement via `random.choices`) and `properties_range` (bounds `properties_served`, in thousands).
- `CONSTRAINT_PRONE_REGIONS` (regions.py) — replaces `LOW_ENGAGEMENT_REGIONS`; currently `{1, 2}` (North + South Scotland).
- `pull_toward_financial_year_start()` — nudges a date a configurable fraction (`strength`) of the way toward the nearest 1 April, then clamps back inside the allowed window.
- `SEASONAL_MULTIPLIER` — a per-calendar-month (1–12) multiplier applied to the expected weekly event count in `generate_usage_events`.
- The usage-events loop now walks real calendar weeks (`while week_start <= today: ... week_start += timedelta(days=7)`) from each account's actual start date, rather than a fixed `range(52)` — this is what makes the seasonal multiplier meaningful (each batch of events is now tied to a real calendar month) and also means an account's total event count naturally reflects how long it's actually been a customer.

**Definition of done (updated):** 450 accounts spread across all 14 regions with realistic relative weighting, `properties_served` populated and scaled sensibly by region, a clear engagement gap between Scotland and the rest, contract signings visibly clustered near financial-year resets, and a winter usage peak that shows up once normalized by active account count.

## Phase 2 — Real data ingestion (Lambda + Step Functions → S3)

### Why

- **Why the Carbon Intensity API's `/regional` endpoint specifically:** one call returns all 14 DNO regions (plus England/Scotland/Wales/GB aggregates — 18 entries total) in a single JSON response — confirmed live and unchanged in structure from what the guide originally assumed. Each region entry carries a stable `regionid` (1–14 for the DNO regions) that lines up exactly with Phase 1's `region_id`, plus `dnoregion`/`shortname` (matching your region names), `intensity` (forecast + index), and `generationmix` (fuel type breakdown). No API key, no auth — one HTTP GET is the whole integration.
- **Why store all 18 entries, unfiltered, in the raw zone:** the 4 aggregate entries (England/Scotland/Wales/GB) don't have a matching `region_id` in Phase 1's accounts table, so they're not useful for the Phase 5 join — but the raw zone's whole purpose is to hold exactly what the API returned, unmodified. Deciding what to keep and what to drop is Phase 3's job (the transform layer), not the ingestion Lambda's. Keeping the Lambda "dumb" (fetch, validate it's JSON, write it, done) means there's only one place business logic can go wrong, and it isn't here.
- **Why `urllib.request` instead of the more common `requests` library:** AWS Lambda's Python runtimes ship with `boto3`/`botocore` pre-installed, but *not* `requests` — using it would mean packaging a dependency into a zip file and uploading that, instead of just pasting code into the console's built-in editor. `urllib` is part of Python's standard library, so it needs zero extra packaging — for a first Lambda, that's one less thing that can go wrong, and it means you can build this entirely through the AWS Console with no zip files at all.
- **Why a separate S3 key per fetch, timestamped down to the second** (`raw/neso-demand/2026-08-17/2026-08-17T14-30-00.json`): S3 objects are immutable by key — writing to the same key twice overwrites the first one. A unique timestamped key per invocation means every historical fetch is preserved, which is exactly what you want for a time-series dataset like this.
- **Why Step Functions wraps a single Lambda, rather than just scheduling the Lambda directly:** you could trigger the Lambda straight from EventBridge with no Step Functions involved — it would work. Wrapping it adds automatic retries (the API being briefly unavailable shouldn't mean a missed day of data) and a visual execution history you can screenshot for your portfolio, at basically zero extra cost (Step Functions' 4,000 free monthly state transitions comfortably covers a Lambda you're calling once a day or even every 30 minutes). It's also exactly where the distribution-level Lambda plugs in later, as a second branch in the same workflow — not a decision you want to retrofit once you're already scaling this into a multi-branch workflow.
- **Why daily to start, not the full 30-minute settlement-period cadence:** the guide's Phase 2 plan mentions both. Daily is the better starting cadence while you're learning the AWS console — fewer executions to reason about while you're checking things work, comfortably inside every free-tier limit, and trivial to tighten to 30 minutes later (it's one field in the EventBridge schedule, not a code change).
- **Why a boto3 deploy script instead of the AWS Console's inline code editor:** the original plan here was console copy-paste — genuinely the simplest possible first deploy, and still how the Step Functions definition below gets deployed. But it means the console, not the repo, is the actual source of truth for what code is running: edit in the console and forget to copy it back into VS Code, and the repo silently goes stale — the exact failure mode a version-controlled "record of what's deployed" is meant to prevent, and the reason for switching before any code was actually pasted in. `infra/deploy_neso_ingest.py` fixes that the way a team that keeps Lambda code and config in a repo typically would: the handler code and its AWS configuration (runtime, memory, IAM role and permissions) both live in the repo as plain files, and a small boto3 script pushes them to AWS. Every deploy becomes a `git`-trackable action, and the console becomes somewhere you go to *observe* the function (logs, test runs), not edit it. It's not a full infrastructure-as-code framework (that's AWS SAM or CDK — a bigger jump, worth considering later once this pattern feels familiar) but it removes the console as a hidden source of truth, which is the part that actually matters for a "record of our Lambda code and config" habit.

### How

**1. The Lambda's own code already lives in your repo:** `ingestion/lambdas/neso_ingest/handler.py` and a placeholder `requirements.txt` (empty — no third-party dependencies needed inside the Lambda itself, see Why above). Alongside it, `infra/` holds everything about how that code gets deployed and run on AWS: `neso_ingest_state_machine.json` (the Step Functions definition, unchanged from before), and three new files — `neso_ingest_lambda_config.json` (the Lambda's settings: function name, runtime, memory, timeout, IAM role name, S3 bucket), `neso_ingest_trust_policy.json` (a small fixed IAM policy the role needs), and `deploy_neso_ingest.py` (the script that does the actual deploying — see Step 4). Save all three new files into your `infra/` folder now. 📝 Open `ingestion/lambdas/neso_ingest/handler.py` in VS Code to read through it before deploying anything — it's short, and worth understanding line by line before it's running unattended on a schedule.

**2. Create the S3 bucket.**
🌐 **Browser (AWS Console):**
1. Search "S3" in the top search bar → **Create bucket**
2. Bucket name: something globally unique, e.g. `gridwatch-raw-<your-name-or-a-few-random-characters>` (S3 bucket names are unique across *all* of AWS, not just your account, so a plain name like `gridwatch-raw` will almost certainly already be taken)
3. AWS Region: **eu-west-2 (London)** — matches the region you set in `aws configure` back in Section 1.1
4. Leave **Block all public access** ticked (the default) — this data should never be public
5. Leave everything else default → **Create bucket**
6. Note the exact bucket name down somewhere — you'll paste it into two places next

**3. Put the bucket name in both places that need it.** There are two separate copies of the bucket name in the repo, for two separate reasons — they must match exactly, or the Lambda will fail with an access-denied error the first time it tries to write:
- 📝 **File — `ingestion/lambdas/neso_ingest/handler.py`:** find the line `S3_BUCKET = "your-bucket-name"` near the top and replace `"your-bucket-name"` with your real bucket name from Step 2. This is what the *running Lambda* uses at request time to know where to write.
- 📝 **File — `infra/neso_ingest_lambda_config.json`:** set `"s3_bucket"` to the same exact bucket name. This is what the *deploy script* uses at deploy time to build the IAM permission that lets the Lambda write there at all.

Save both files.

**4. Deploy the Lambda straight from the repo — no console paste required.**
🖥️ **Terminal** (`.venv` activated, inside `gridwatch`):
```
pip install boto3
```
This is a one-off local install, separate from the empty `requirements.txt` inside `ingestion/lambdas/neso_ingest/` — that one lists what ships *inside* the Lambda (deliberately nothing, see Why above); this `boto3` is a tool you run on your own machine to talk *to* AWS, not code the Lambda itself runs. (The Lambda's own runtime already has `boto3` built in.)

Before running the script, open `infra/neso_ingest_lambda_config.json` and check every value:
- `s3_bucket` — must exactly match your Step 2 bucket name (see Step 3 above)
- `handler` — must be `<filename-without-.py>.<function-name>`. Open `handler.py` and find the line defining the main function, e.g. `def lambda_handler(event, context):` — if yours is named differently, update `"handler"` in the config to match (`handler.lambda_handler` is only a placeholder assumption)
- `region`, `function_name`, `role_name` — fine to leave as-is unless you have a reason to change them

Then run the deploy script:
🖥️ **Terminal:**
```
python infra/deploy_neso_ingest.py
```
This does everything the original Steps 4-6 did by hand in the console: creates an IAM execution role (with CloudWatch Logs access plus the S3 write permission, built from `s3_bucket` in the config), zips up `handler.py`, and creates the Lambda function from that zip. You'll see progress printed as it runs — `Created IAM role...`, `Waiting 10s for the new role to finish propagating...`, `Created new Lambda function...`.

**From now on, every time you change `handler.py`:** save the file, then just re-run `python infra/deploy_neso_ingest.py` again — it detects the function already exists and updates its code and config instead of creating it fresh. That re-run is your whole edit-deploy loop; the AWS Console is for reading logs and test results, not for editing code.

**5. Test it manually, before scheduling anything.**
🌐 **Browser (AWS Console), on the function's page (search "Lambda" → click `gridwatch-neso-ingest`):**
1. Click the **Test** tab
2. **Event name:** anything, e.g. `manual-test`. Leave the JSON body as the default template (`{}`) — this Lambda ignores its input entirely, it always does the same thing
3. Click **Save**, then click **Test**
4. You should see **Execution result: succeeded**, with a response showing the `bucket` and `key` your function wrote to
5. Confirm it for real: search "S3" → open your bucket → browse into `raw/neso-demand/` → you should see today's date folder, and inside it a `.json` file. Open it (Download, or click **Open**) and check it looks like real Carbon Intensity data — a `data` array containing a `regions` array with 18 entries

**6. Create the Step Functions state machine.** First, find your AWS account ID (you'll need it for the next step): 🖥️ **Terminal:** `aws sts get-caller-identity` — the `Account` field in the output.
🌐 **Browser (AWS Console):**
1. Search "Step Functions" → **State machines** → **Create state machine**
2. Choose to write it in code (look for **Code** / **Definition** as the editing mode, rather than the visual drag-and-drop designer)
3. Paste in the contents of `infra/neso_ingest_state_machine.json`, but first replace `YOUR_ACCOUNT_ID` in that ARN with your real account ID from the command above (leave `eu-west-2` and `gridwatch-neso-ingest` as they are, assuming you named things exactly as above)
4. Type: **Standard**
5. Name: `gridwatch-neso-ingestion`
6. When asked about permissions, let it **create a new IAM role** — Step Functions will detect the Lambda referenced in your definition and generate a role scoped to invoke just that function
7. **Create state machine**

**7. Test the state machine.**
🌐 **Browser (AWS Console), on the state machine's page:**
1. Click **Start execution** → leave the input as the default `{}` → **Start execution**
2. Watch the execution graph — the single state should turn green (succeeded) within a few seconds
3. Check S3 again for a new object — confirms the whole chain (Step Functions → Lambda → S3) works end to end

**8. Schedule it with EventBridge.**
🌐 **Browser (AWS Console):**
1. Search "EventBridge" → look for **Scheduler** in the left-hand navigation (the newer, more flexible way to schedule things — if your console shows a different layout by the time you're doing this, search for "schedule" or "rule" and look for anything that lets you target a Step Functions state machine on a timer)
2. **Create schedule**
3. Name: `gridwatch-neso-daily`
4. Schedule pattern: **Recurring schedule** → rate-based, **1 day** (you can tighten this to a 30-minute cadence later — see the Why section)
5. Target: **Step Functions** → **StartExecution** → select `gridwatch-neso-ingestion`
6. Permissions: let it auto-create the role needed to start the state machine
7. **Create schedule**

**9. Verify end to end, then commit.** Wait for the next scheduled run (or trigger it manually the same way as Step 7 to confirm sooner), check S3 for the new object, then commit `ingestion/` and `infra/` to a feature branch and merge — same pattern as Phase 1.

**Definition of done:** raw NESO data landing reliably in S3 on a schedule with no manual intervention, a Step Functions execution graph you can screenshot for your portfolio, and the Lambda's code *and* its AWS configuration (IAM role, memory, timeout) version-controlled in the repo and deployed with a repeatable `python infra/deploy_neso_ingest.py` rather than pasted into the console by hand.

### What — argument and concept reference

- **ARN (Amazon Resource Name)** — AWS's unique identifier format for any resource, e.g. `arn:aws:lambda:eu-west-2:123456789012:function:gridwatch-neso-ingest` — service (`lambda`), region, account ID, resource type and name, in that order. The Step Functions definition needs your Lambda's exact ARN to know what to invoke.
- **IAM inline policy** — a permissions policy attached directly to one specific role, rather than a reusable "managed policy" you might attach to many roles. Fine for a single-purpose role like this Lambda's. `deploy_neso_ingest.py` creates this one (the S3 write permission) programmatically instead of you pasting JSON into the console.
- **`s3:PutObject`** — the specific IAM permission for writing a new object to S3; narrower than blanket S3 access, and scoped further here to just your one bucket via the `Resource` ARN.
- **boto3** — AWS's official Python SDK (Software Development Kit); lets Python code call AWS APIs directly (create a role, deploy a function, and so on) instead of clicking through the console. `infra/deploy_neso_ingest.py` uses it for everything — `boto3.client("iam")` and `boto3.client("lambda")` are the two "clients" it talks to.
- **Trust policy (`AssumeRolePolicyDocument`)** — a special kind of IAM policy attached to a *role* rather than a *user*, saying who or what is allowed to "become" that role. `infra/neso_ingest_trust_policy.json`'s `Principal: {"Service": "lambda.amazonaws.com"}` means only the Lambda service itself can assume this role — separate from the *permissions* policies (like the S3 write one above) that say what the role can do once assumed.
- **AWSLambdaBasicExecutionRole** — an AWS-managed policy (maintained centrally by AWS, rather than written by you) granting just enough CloudWatch Logs access for a Lambda to write its own execution logs. Every Lambda needs at least this; `deploy_neso_ingest.py` attaches it automatically.
- **IAM eventual consistency** — a newly created IAM role isn't always immediately usable everywhere — AWS's identity data takes a few seconds to finish propagating. `deploy_neso_ingest.py`'s 10-second wait after creating a new role is a pragmatic accommodation for this, not a bug; it only happens on the very first deploy.
- **Amazon States Language (ASL)** — the JSON-based language Step Functions state machine definitions are written in. `StartAt` names the first state; `States` is a dictionary of every state in the workflow, keyed by name; `Type: "Task"` means "run something" (here, invoke a Lambda); `End: true` marks a state as the workflow's last step.
- **`Retry` block** — `ErrorEquals: ["States.ALL"]` matches any error type; `IntervalSeconds`/`MaxAttempts`/`BackoffRate` control how long to wait before retrying, how many times, and how much longer to wait after each failed attempt (exponential backoff).
- **EventBridge Scheduler** — AWS's dedicated scheduling service (distinct from the older "EventBridge Rules" you may see referenced elsewhere) for triggering something — here, a Step Functions execution — on a recurring or one-off schedule.
- **Execution role** — the IAM role a Lambda function (or state machine) runs as; determines what AWS resources it's allowed to touch, separately from your own IAM user's permissions.

## Phase 3 — Transform (cost-aware Glue → curated S3)

**What you're building:** cleaned, validated, partitioned data, ready to load.

**The cost trade-off, addressed directly:**
- **Recommended path:** use a **Glue Python Shell job** (not Spark) at the smallest DPU setting (0.0625 DPU). This is the cheapest Glue compute option — a fraction of a penny per short run — and still gives you real, CV-legitimate Glue experience. Trigger it as the next step in your Step Functions workflow.
- **Alternative if you want strictly £0:** do the transform inside the same Lambda functions from Phase 2 (pandas/pyarrow) instead, and run a **Glue Crawler** occasionally just to register schemas in the (free) Data Catalog. Noting in your write-up that you evaluated the Glue-vs-Lambda cost trade-off and made a deliberate choice is itself a legitimate, CV-worthy architectural decision.

**What the transform does either way:** parse raw JSON/CSV, handle missing or malformed readings, filter Phase 2's raw feed down to just the 14 real DNO regions (dropping the England/Scotland/Wales/GB aggregate entries, which don't have a matching `region_id` in Phase 1's data), cast types correctly, convert settlement periods to proper timestamps, and write out as **partitioned Parquet** (partitioned by date) into a `curated/` S3 prefix.

**An honesty note for later:** you won't have access to real substation capacity thresholds (that's internal DNO data), so "stress" in this project should be framed as a *relative* measure — e.g. top-percentile load periods for a given substation/region — rather than claiming to know true remaining capacity. Say this explicitly in your write-up; it reads as more credible, not less.

**Definition of done:** curated, partitioned Parquet in S3, registered in the Glue Data Catalog, ready to load.

## Phase 4 — Load into BigQuery (star schema)

**What you're building:** the analytical warehouse.

**Schema** (using `region_id` throughout as the shared key from Phase 1):
- `fact_network_readings`: timestamp, region_id, demand_or_consumption, generation_mix, carbon_intensity, relative_load_percentile
- `fact_user_engagement`: user_id, timestamp, event_type
- `dim_date`, `dim_region` (region_id, region_name), `dim_account`, `dim_user`

**Step-by-step** (you can start this with just Phase 1's CSVs, before the AWS side is built — good way to start practicing SQL early):

**1. Create your dataset**, if you haven't already:
🖥️ **Terminal:**
```
bq mk --dataset --location=europe-west2 your-project-id:gridwatch
```

**2. Create the tables with an explicit schema** — safer than letting BigQuery auto-detect types from a CSV, which sometimes guesses wrong:
🖥️ **Terminal:**
```
bq mk --table your-project-id:gridwatch.dim_region region_id:INTEGER,region_name:STRING
bq mk --table your-project-id:gridwatch.accounts account_id:INTEGER,account_name:STRING,region_id:INTEGER,contract_tier:STRING,contract_start_date:DATE,renewal_date:DATE,churn_date:DATE,properties_served:INTEGER
```
(repeat the pattern for `users` and `usage_events`, matching the columns from Phase 1's CSVs)

**3. Load the CSVs directly:**
🖥️ **Terminal:**
```
bq load --source_format=CSV --skip_leading_rows=1 your-project-id:gridwatch.accounts mock_data/output/accounts.csv
```
Repeat for `users.csv` and `usage_events.csv`.

**4. Verify it loaded correctly:**
🖥️ **Terminal:**
```
bq query --use_legacy_sql=false 'SELECT region_id, COUNT(*) AS accounts FROM `your-project-id.gridwatch.accounts` GROUP BY region_id ORDER BY region_id'
```
You should see all 14 `region_id` values represented — matching what you checked in Phase 1, Step 8.

**5. Later, once real NESO/curated data lands from the AWS side (Phase 2/3):** load it the same way, but point `bq load` at a `gs://your-bucket/...` path with `--source_format=PARQUET` instead of a local CSV.

Partitioning and clustering by date is worth setting up once you're loading real time-series data — for the mostly-static `accounts`/`users` tables from Phase 1, it isn't necessary yet.

**Definition of done:** all three Phase 1 tables queryable in BigQuery, with the `region_id` GROUP BY confirming the join key lines up cleanly, comfortably inside the 10 GB free storage limit.

## Phase 5 — SQL analysis

The core "data analysis and manipulation" competency shows up here. Suggested questions:

1. **Identify stress:** which regions/substations show the highest load volatility or most frequent peak-load periods, based on the real UK Power Networks and NESO data?
2. **Engagement gap:** do accounts responsible for higher-stress regions show higher or lower product engagement (logins, alert acknowledgements) than accounts in lower-stress regions?
3. **Renewal risk:** is there a relationship between low engagement and non-renewal (churn) — specifically, are disengaged accounts in high-stress regions a renewal risk despite being the customers who most need the product?

Techniques you'll naturally end up using: window functions for cohort/retention analysis, joins across your fact tables, CTEs (Common Table Expressions — named, temporary result sets that break a complex query into readable steps) to keep multi-step logic readable, and date bucketing to align usage events with settlement periods. Given the Phase 1 addendum's growth-vs-seasonality confound (see above), normalizing engagement metrics by active account count or account tenure will likely matter here too, not just for usage-event seasonality.

**Definition of done:** a small set of saved SQL queries with clear, written-up findings. A null result ("no strong relationship found") is a legitimate and honest finding — don't feel pressure to manufacture a stronger story than the data supports.

## Phase 6 — Business case write-up

Structure it like a real stakeholder memo, not a technical report:

1. **Problem statement** — one paragraph, plain English.
2. **Method** — brief, non-technical summary of the data and approach.
3. **Findings** — 2-4 key results, ideally each with a simple chart.
4. **Recommendation** — a concrete action (e.g. "prioritize proactive customer-success outreach for accounts in high-stress, low-engagement regions"), with your best estimate of impact based on the data.
5. **Next steps / limitations** — honest about what the mock and proxied data can and can't tell you.

This document is arguably the single most CV-valuable artifact in the whole project: proof you can go from raw data to a business decision, not just move data around.

---

# Suggested pace

No fixed timeline, but roughly: Part 1 (environment setup) is a couple of focused sessions. Phase 1 is a single sitting once the environment's ready. Phases 2-4 (the AWS + BigQuery pipeline) are the bulk of the real work — comfortable over a couple of weeks part-time. Phases 5-6 move faster once data is flowing. It's fine to list this as "in progress" on your CV once Phases 1-2 are done — an in-flight, demonstrable project is a perfectly normal thing to show.

# Where to start right now

Part 1.1 — the AWS account and IAM setup — since everything downstream depends on it. Once that's done, Phase 1 (mock data) has no dependencies on anything else and is a good next win. Ask whenever you're ready to move to the next piece.

---

# Appendix — Glossary of terms

Terms you'll run into throughout this guide and in day-to-day data engineering work, grouped by area.

## Energy industry
- **DNO (Distribution Network Operator)** — the company that owns and runs the local electricity network in a region, delivering power the "last mile" to homes and businesses.
- **TSO (Transmission System Operator) / NESO** — responsible for the national, high-voltage grid that moves power over long distances between generators and DNOs. In Great Britain, this role is NESO (National Energy System Operator).
- **T&D** — shorthand for "Transmission & Distribution," the two halves of getting electricity from a power station to your building.
- **BMRS** — Balancing Mechanism Reporting Service, Elexon's data platform showing how the grid balances electricity supply and demand in near-real time.
- **Carbon intensity** — how much CO2 is produced per unit of electricity generated at a given moment; it changes constantly as the generation mix (wind/solar/gas/etc.) shifts.
- **Settlement period** — the 30-minute windows GB's electricity market is priced and balanced in.
- **GSP (Grid Supply Point)** — the physical point where the national transmission network connects into a regional distribution network.
- **Curtailment / constraint payments** — paying a generator (typically a wind farm) to reduce or stop output because the transmission grid can't carry all the power it's producing to where it's needed. GB-wide constraint costs were roughly £1.5bn in 2024 and £1.8bn in 2025, with Scotland accounting for a disproportionate share due to high wind generation outpacing north-south transmission capacity.
- **RIIO-ED2** — Ofgem's current electricity distribution price control period (2023–2028), setting the ~£22bn of allowed DNO investment and, by extension, DNOs' 5-year capital/budget planning cycle.

## Business / SaaS
- **SaaS (Software as a Service)** — a business model where customers pay an ongoing subscription to use software hosted by someone else, rather than buying and installing it themselves.
- **B2B (Business-to-Business)** — a company selling to other organisations, as opposed to individual consumers (B2C).
- **Churn** — the rate at which customers cancel or fail to renew.
- **Cohort analysis** — grouping customers by a shared starting point (e.g. signup month) to compare how their behaviour evolves over time.

## Cloud / AWS
- **IAM (Identity and Access Management)** — AWS's system for controlling who, or what, can access which resources.
- **CLI (Command Line Interface)** — controlling software by typing text commands rather than clicking buttons.
- **ARN (Amazon Resource Name)** — a unique identifier AWS gives every resource you create.
- **MFA (Multi-Factor Authentication)** — requiring a second proof of identity (e.g. a phone code) alongside your password.
- **DPU (Data Processing Unit)** — AWS Glue's unit of compute power; Glue job costs are billed per DPU-hour.
- **Lambda** — AWS's "serverless" compute service: you upload code and it runs on demand, without you managing a server.
- **Serverless** — cloud services that run your code without you provisioning or managing the underlying machine yourself.
- **EventBridge** — AWS's scheduling/event-routing service; used here to trigger the pipeline on a timer.
- **Step Functions** — AWS's service for orchestrating multiple steps (e.g. several Lambdas) in a defined order, with built-in retry and error handling.
- **boto3** — AWS's official Python SDK; the library `infra/deploy_neso_ingest.py` uses to create and update AWS resources directly from Python instead of the console.

## Data engineering / SQL
- **ETL / ELT** — Extract, Transform, Load (or Extract, Load, Transform) — the general pattern of pulling data from a source, cleaning/reshaping it, and putting it somewhere useful.
- **Star schema** — a common data warehouse design: a central "fact" table of events/measurements, surrounded by "dimension" tables of descriptive context (e.g. date, region).
- **Fact table / dimension table** — a fact table holds numeric events or measurements (e.g. a meter reading, a usage event); a dimension table holds descriptive attributes you'd filter or group by (e.g. region names, account details).
- **Partitioning** — physically splitting a table's data (e.g. by date) so queries only scan the relevant slice instead of the whole table.
- **Clustering** — sorting data within a table by a chosen column so similar rows sit together, speeding up filtered queries.
- **CTE (Common Table Expression)** — a named, temporary result set defined with `WITH ... AS (...)` at the start of a query, used to break complex SQL into readable steps.
- **Window function** — a SQL function (e.g. running total, rank) calculated across a set of related rows without collapsing them into one result, unlike a normal aggregate.
- **Parquet** — a compressed, column-oriented file format built for fast analytical querying, as opposed to CSV (row-oriented, uncompressed, human-readable).
- **Data Catalog** — a searchable index of what datasets/tables exist and their structure; Glue's version registers schemas so other AWS services can find them.
- **Raw / curated (or "staging") zone** — a common convention: "raw" holds data exactly as ingested, unmodified; "curated" holds cleaned, transformed data ready for downstream use.

## Git / GitHub
- **Repo (repository)** — the project folder whose history Git is tracking.
- **Commit** — a saved snapshot of your changes, with a short message describing what changed.
- **Push / pull** — sending your local commits up to GitHub (push), or bringing down others' commits from GitHub (pull).
- **Stage / staging (in Git)** — marking specific changes as "ready to be included in the next commit." Note this is a different meaning to the "staging zone" in data engineering above — same word, different context.
- **Branch** — a parallel, independent line of changes in a repo, typically used to build something without affecting the main version until it's ready.
- **Merge** — folding one branch's commits into another (typically a feature branch back into `main`).
- **Pull request (PR)** — a GitHub page proposing that one branch be merged into another, showing the diff and allowing comments, before the merge actually happens.
