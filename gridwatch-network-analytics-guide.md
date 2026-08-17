# GridWatch: UK Network Analytics — Personal Data Engineering Project

*(A working name — swap it out anywhere with a find-and-replace if you land on something better. "LoadSight" and "CircuitScope" are two other options in the same vein if you want alternatives.)*

A complete, self-contained build guide: environment setup through to a finished business case. Everything you need is in this one document.

**The concept:** GridWatch is a mock B2B (business-to-business — selling to companies, not individual consumers) SaaS (Software as a Service — a subscription-based software product) product sold to DNOs (Distribution Network Operators — the companies that run the local electricity network in a region) and specifically their asset planning and network operations teams. It gives them a live dashboard of network loading across their region, built from real grid data, with alerts when a substation or feeder looks like it's trending toward stress. Your "customers" are operations teams (accounts), your "users" are the engineers who log in and use it day to day.

**The business problem:** Do the accounts responsible for the highest-stress network regions actually engage with the product — or are the regions that most need proactive monitoring also the ones at highest risk of the customer not renewing? If there's a gap, what would you recommend to close it?

This mirrors real T&D-sector data work closely: you'll be handling genuine transmission and distribution data, building the kind of platform that a company selling into DNOs (Distribution Network Operators) or National Energy System Operator-adjacent services might actually build.

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
├── infra/                      (Step Functions state machine definitions, EventBridge schedule config)
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
It should return your IAM user's account ID and ARN (Amazon Resource Name — a unique ID AWS gives every resource you create), confirming the CLI is correctly authenticated against your new user.

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
3. Create each of these, one at a time: `ingestion`, `transform`, `infra`, `warehouse`, `mock_data`, `notebooks`, `docs`, `tests` (see the **Repository structure** section above for what each is for)
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

### Step 12: Making changes day-to-day
**Using VS Code's Source Control panel:**
1. Edit any file and save it (Ctrl/Cmd+S)
2. Click the Source Control icon in the sidebar
3. Hover over a changed file and click the **+** that appears (this "stages" it) — or click the **+** next to "Changes" at the top to stage everything at once
4. Type a short commit message in the text box at the top of the panel
5. Click the blue **✓ Commit** button
6. Click **Sync Changes** (appears afterward, at the bottom) to push it to GitHub

**Using GitHub Desktop instead — exactly the same result, different buttons:**
1. Switch to GitHub Desktop — your changed files appear automatically
2. Type a commit message in the bottom-left box
3. Click **Commit to main**
4. Click **Push origin** at the top

Use whichever one feels more natural at the time — they update the same repository either way.

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
- **Why `faker` and `pandas` specifically:** `faker` generates realistic fake data (names, companies, dates) so you're not hand-typing 250 company names yourself. `pandas` is the standard Python tool for tabular data — you'll use it again in Phase 5, so it's worth the familiarity now, on data you already understand.
- **Why one file, built up in pieces, rather than several small ones:** a Python file runs top to bottom when executed, and a function has to be *defined* before it's *called*. Keeping the three table-generating functions and the code that calls them in one file makes that ordering visible and easy to follow while you're still learning the pattern — you can split it into multiple files later once it feels natural.
- **Why the specific design choices in the `accounts` table:** an 18-month signup window (not literally today) ensures every account already has some usage history for Phase 5 to analyze. A 15% baseline churn rate gives you a believable mix of active and lost customers. Weighting toward the cheapest tier (50% Basic) mirrors how real SaaS customer bases are actually shaped — most customers on the entry plan, fewer on the expensive one.
- **Why the "low engagement regions" trick in `usage_events`:** Phase 5's whole analysis depends on there being *some* real pattern buried in this data to find with SQL. If every account behaved identically, there'd be nothing to discover. Making 4 of the 14 regions quietly less engaged — not obviously, just a tendency — is a deliberate puzzle you're setting for your future self.
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
That file is done — you won't touch it again in this phase, only import from it.

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

### What — argument and concept reference

**`regions.py`:** this is a *list* (square brackets `[ ]`) containing *dictionaries* (each `{ }` entry) — a dictionary is a set of labelled values, like `region_id: 1` paired with `region_name: "North Scotland"`. This shape — a list of dictionaries — is reused throughout `generate_data.py`, and it's exactly what pandas expects when converting to a table in Step 7.

**Accounts function:**
- `Faker("en_GB")` — `Faker` is a class from the faker library; calling it creates a "faker object" you ask to generate fake data from. `"en_GB"` is the locale argument — British-style company names/addresses rather than the American default.
- `random.seed(42)` — one argument, a starting number for the random generator. Any fixed number works; what matters is that the *same* seed always reproduces the *same* "random" data, useful while tuning. Delete this line once you're happy with the results, so future runs are genuinely fresh.
- `random.choice(REGIONS)` — one argument, a list; returns a single random item from it.
- `fake.date_between(start_date="-18m", end_date="-1m")` — `start_date`/`end_date` are keyword arguments; Faker accepts relative strings like `"-18m"` (18 months ago) instead of you calculating an actual date.
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

**Knobs to adjust, if you want more variety** (all in `generate_data.py`):
- Region weighting: swap `random.choice(REGIONS)` for `random.choices(REGIONS, weights=[...])` so London/South East get more accounts than North Scotland
- Seasonality: raise `base_events_per_week` for winter weeks — higher real electricity demand tends to mean more alerts, hence more logins
- `TIER_WEIGHTS`: shift these so Enterprise accounts get systematically more users/events, not just a higher price

**Definition of done:** three CSVs in `mock_data/output/`, covering a full year, `region_id` as a clean shared key ready to join against NESO data, and a genuine (if noisy) engagement gap between regions for Phase 5 to find.

## Phase 2 — Real data ingestion (Lambda + Step Functions → S3)

**What you're building:** scheduled ingestion of real transmission-level grid data, landing as raw JSON/CSV in S3. Starting with a single source keeps this phase tractable — distribution-level data comes in as a natural extension once this pipeline pattern is proven, not as a blocker to getting something working end-to-end.

**Data source — transmission-level (start here):**
- **NESO (National Energy System Operator) Data Portal & Carbon Intensity API** — GB-wide (GB = Great Britain here, not gigabyte) and regional demand, generation mix, carbon intensity, and balancing/constraint data. No authentication required, and its ~14 regions give you a genuine "region" dimension for the Phase 5 analysis without needing a second source yet.

**Distribution-level data — add later, as a Phase 2 extension:**
- **UK Power Networks Smart Meter Consumption (Open Data)** — aggregated half-hourly consumption at substation/LV feeder level. Once the transmission pipeline is working, add this the same way: another Lambda, another branch in the Step Functions workflow, another prefix in S3. It deepens the "network stress" picture from regional down to substation level.

*(Optional further stretch: Elexon's Insights Solution/BMRS (Balancing Mechanism Reporting Service) APIs add settlement-level pricing and balancing-cost data eventually — not required for the core story.)*

**How (for the NESO source):**
1. Write a Lambda function (Python) that calls the API and writes the raw response to S3, keyed by date — e.g. `raw/neso-demand/2026-08-15.json`.
2. Wrap it in a **Step Functions Standard workflow** — even a single-Lambda workflow is worth doing properly here, since it gives you retry/error handling and a visual execution graph, and it's exactly where you'll plug in the distribution branch later.
3. Trigger it on a schedule via **EventBridge** — every 30 minutes to match settlement periods, or daily if you'd rather keep volume low while learning.

**Free-tier math:** even at hourly frequency you're around 700-750 invocations per month — nowhere near the 1M free requests. Daily Step Functions runs land around 30 transitions/month, well under the 4,000 free limit.

**Definition of done:** raw NESO data landing reliably in S3 on schedule, with a Step Functions execution graph you can screenshot for your portfolio.

## Phase 3 — Transform (cost-aware Glue → curated S3)

**What you're building:** cleaned, validated, partitioned data, ready to load.

**The cost trade-off, addressed directly:**
- **Recommended path:** use a **Glue Python Shell job** (not Spark) at the smallest DPU setting (0.0625 DPU). This is the cheapest Glue compute option — a fraction of a penny per short run — and still gives you real, CV-legitimate Glue experience. Trigger it as the next step in your Step Functions workflow.
- **Alternative if you want strictly £0:** do the transform inside the same Lambda functions from Phase 2 (pandas/pyarrow) instead, and run a **Glue Crawler** occasionally just to register schemas in the (free) Data Catalog. Noting in your write-up that you evaluated the Glue-vs-Lambda cost trade-off and made a deliberate choice is itself a legitimate, CV-worthy architectural decision.

**What the transform does either way:** parse raw JSON/CSV, handle missing or malformed readings, cast types correctly, convert settlement periods to proper timestamps, and write out as **partitioned Parquet** (partitioned by date) into a `curated/` S3 prefix.

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
bq mk --table your-project-id:gridwatch.accounts account_id:INTEGER,account_name:STRING,region_id:INTEGER,contract_tier:STRING,contract_start_date:DATE,renewal_date:DATE,churn_date:DATE
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

Techniques you'll naturally end up using: window functions for cohort/retention analysis, joins across your fact tables, CTEs (Common Table Expressions — named, temporary result sets that break a complex query into readable steps) to keep multi-step logic readable, and date bucketing to align usage events with settlement periods.

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
