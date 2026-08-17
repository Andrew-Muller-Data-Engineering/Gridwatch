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
- **Why extend the same boto3-deploy pattern to Step Functions and EventBridge, rather than stopping at the Lambda:** the exact same argument applies here — pasting the state machine's ASL into the console, or clicking through EventBridge Scheduler's UI, works fine once, but leaves the console as the only place either resource's real configuration lives, exactly the problem just solved for the Lambda. `infra/deploy_stepfunctions.py` follows the identical shape as the Lambda's deploy script — declarative JSON config plus trust policies plus a boto3 script that creates-or-updates — so by the end of Phase 2 there's one consistent pattern across every AWS resource in the project, not a different workflow per service. It also removes the one genuinely manual, error-prone step from the original plan — hand-copying your AWS account ID into the state machine's Lambda ARN — since the script now looks it up itself via STS (Security Token Service — the AWS API for asking "who am I currently authenticated as").
- **Why a fixed daily time (9am, Europe/London) rather than a rolling 24-hour interval:** EventBridge's `rate(1 day)` expression is anchored to whenever the schedule happened to be created, not a specific clock time — perfectly fine for testing, but not what you'd want for something meant to double as a daily reporting feed, where a predictable, fixed local time matters more than the exact interval between runs. Switching to a `cron(0 9 * * ? *)` expression with an explicit `Europe/London` timezone fixes the run to 9am local time year-round, correctly adjusting for BST/GMT — a cron expression alone is evaluated in UTC, so without the timezone setting, "9am" would quietly become "9am UTC" and drift by an hour every time the clocks change.

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

**6. Deploy the Step Functions state machine and its EventBridge schedule — again straight from the repo, no console paste required.** Alongside `infra/neso_ingest_state_machine.json` (the workflow definition itself, unchanged from before), your `infra/` folder now also holds `neso_ingest_stepfunctions_config.json` (settings for both the state machine and its schedule), `neso_ingest_stepfunctions_trust_policy.json` and `neso_ingest_scheduler_trust_policy.json` (the trust policy each resource's own role needs), and `deploy_stepfunctions.py` (the script that deploys all of it). Save these into your `infra/` folder now if you haven't already — see `docs/infra-cheatsheet.md` for a full explanation of what each individual file does.

Before running it, open `infra/neso_ingest_stepfunctions_config.json` and check the values match your setup:
- `lambda_function_name` — must match the function name from Step 4 above (`gridwatch-neso-ingest` unless you changed it)
- `region` — must match wherever you deployed the Lambda (`eu-west-2` unless you changed it)
- `schedule_expression` and `schedule_expression_timezone` — already set to `cron(0 9 * * ? *)` and `"Europe/London"`, a fixed 9am-UK-time daily run (see Why above for why a cron expression plus an explicit timezone, rather than a simple rate). Change these two values if you'd prefer a different time or cadence.

🖥️ **Terminal** (`.venv` activated, inside `gridwatch`):
```
python infra/deploy_stepfunctions.py
```
This does everything the original Steps 6-8 did by hand in the console: looks up your AWS account ID and the Lambda's ARN automatically (no more manually replacing `YOUR_ACCOUNT_ID` yourself), creates the state machine's execution role (scoped to just `lambda:InvokeFunction` on your one function) and the state machine itself, then creates the schedule's own execution role (scoped to just `states:StartExecution` on your one state machine) and the schedule itself. You'll see progress printed as it runs — `Created IAM role...`, `Created state machine...`, `Created EventBridge schedule...`.

**From now on, whenever you change the workflow definition or the schedule's cadence:** edit the relevant file, then just re-run `python infra/deploy_stepfunctions.py` again — like the Lambda's deploy script, it detects what already exists and updates it in place instead of creating it fresh.

**7. Test the state machine manually.**
🌐 **Browser (AWS Console):**
1. Search "Step Functions" → **State machines** — first check the region selector in the very top-right corner of the console is set to **eu-west-2 (London)**, or your new state machine won't appear in the list (an easy few minutes to lose if a different region was left selected from an earlier session)
2. Click `gridwatch-neso-ingestion` → **Start execution** → leave the input as the default `{}` → **Start execution**
3. Watch the execution graph — the single state should turn green (succeeded) within a few seconds
4. Check S3 again for a new object — confirms the whole chain (Step Functions → Lambda → S3) works end to end

**8. Confirm the schedule is live.**
🌐 **Browser (AWS Console), same region:**
1. Search "EventBridge" → **Scheduler**
2. Click `gridwatch-neso-daily` and check the **Schedule** section shows your cron expression and `Europe/London` as the timezone
3. Nothing to configure here — this step is only confirming what the script already created matches what you expect

**9. Verify end to end, then commit.** Wait for the next scheduled run (9am UK time, or trigger it manually the same way as Step 7 to confirm sooner), check S3 for the new object, then commit `infra/` to a feature branch and merge — same pattern as Phase 1.

**Definition of done:** raw NESO data landing reliably in S3 on a fixed daily schedule (9am, Europe/London) with no manual intervention, a Step Functions execution graph you can screenshot for your portfolio, and every piece of this — the Lambda's code and config, the state machine definition, and the EventBridge schedule — version-controlled in the repo and deployed with two repeatable scripts (`python infra/deploy_neso_ingest.py`, `python infra/deploy_stepfunctions.py`) rather than pasted or clicked together in the console.

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
- **`rate()` vs. `cron()` expressions** — the two ways to define an EventBridge schedule's cadence. `rate(1 day)` just repeats every fixed interval, counted from whenever the schedule was created — simple, but with no fixed clock time. `cron(0 9 * * ? *)` instead pins the schedule to exact fields (minute, hour, day-of-month, month, day-of-week) — this one means "at minute 0 of hour 9, every day" — giving you a predictable, fixed time of day rather than a rolling interval.
- **`ScheduleExpressionTimezone`** — an IANA timezone name (e.g. `"Europe/London"`) attached to a schedule so its `cron()` expression is evaluated in that local timezone instead of UTC, and automatically adjusts for daylight saving (BST/GMT) without you ever needing to touch the expression itself twice a year.
- **Cross-service IAM role chaining** — the same least-privilege idea from the Lambda's role, now applied at every link in the chain: the Lambda's role can only write to one S3 bucket; the state machine's role can only invoke that one Lambda (`lambda:InvokeFunction`, scoped to its ARN); the schedule's role can only start that one state machine (`states:StartExecution`, scoped to its ARN). No single role in the pipeline can do more than the one specific thing it needs to.
- **`describe_state_machine` / `create_state_machine` / `update_state_machine`, `get_schedule` / `create_schedule` / `update_schedule`** — the boto3 methods `deploy_stepfunctions.py` uses to check whether a resource already exists (an exception means "not found yet") and switch between creating it fresh or updating it in place — the same create-or-update pattern `deploy_neso_ingest.py` uses for the Lambda and its role.

## Phase 3 — Transform (cost-aware Glue → curated S3)

### Why

- **Why a Glue Python Shell job, not Spark (Glue ETL):** Glue's Spark-based ETL jobs are built for genuinely large datasets — they spin up a small cluster, which costs real money even for a job processing a handful of small JSON files. A **Python Shell** job is a single lightweight Python process, billed at Glue's smallest DPU (Data Processing Unit — Glue's unit of compute) tier of 0.0625 DPU — a fraction of a penny per run — while still using the real AWS Glue service, so it's genuine, CV-legitimate Glue experience rather than a workaround that avoids Glue entirely. For GridWatch's actual daily volume (18 small region readings, once a day), Spark would be solving a problem this project doesn't have.
- **Why chain the transform into the same Step Functions workflow, rather than a separate schedule:** the two steps are genuinely sequential — the transform has nothing to read until ingestion has run — so representing that as one workflow (`InvokeNesoIngestLambda` → `RunNesoTransformGlueJob`) rather than two independently-scheduled resources hoping to line up in the right order is both more correct and gives you one execution graph to screenshot for your portfolio, showing the whole daily pipeline rather than just one slice of it. Step Functions' 4,000 free monthly state transitions comfortably cover two states running once a day.
- **Why the extra `.sync` in the Glue step's `Resource` ARN (`arn:aws:states:::glue:startJobRun.sync`) matters:** without `.sync`, Step Functions would call the Glue `StartJobRun` API, get back "started," and immediately mark that state as *succeeded* — regardless of whether the job goes on to actually finish or fail a minute later. `.sync` tells Step Functions to keep watching and only mark the state complete once the Glue job itself finishes, and to mark it *failed* if the Glue job fails. For a state whose entire purpose is "did the transform actually work," that distinction is the difference between a meaningful success signal and a rubber stamp.
- **Why the state machine's role needed new permissions, not a second role:** the workflow itself grew from one step to two, so the identity running that workflow needs permission to do the new thing — same principle as every other role in this project, just applied to a role you'd already created. The new permissions are still scoped as narrowly as everything else: `glue:StartJobRun`/`GetJobRun`/`BatchStopJobRun` on exactly one Glue job's ARN, plus a small `events:PutRule`/`PutTargets`/`DescribeRule` allowance scoped to one specific AWS-managed rule name (`StepFunctionsGetEventForGlueJobRunRule`) that Step Functions creates and uses internally to know when a `.sync` Glue job finishes, rather than polling. That EventBridge rule isn't a resource you ever create or see directly — it's plumbing AWS's `.sync` integration manages for you, and the permission just lets it do that.
- **Why extend the same config-plus-trust-policy-plus-deploy-script pattern to Glue:** the same argument as Phase 2's Step Functions/EventBridge extension — one consistent shape across every AWS resource in the project. The one genuine difference: a Glue job doesn't run code straight from your repo the way a Lambda does — Glue reads its script from an S3 location — so `deploy_glue_transform.py` has one extra job the earlier scripts didn't: re-uploading the script to S3 on every deploy, so the S3 copy can never quietly drift from what's in the repo (the exact failure mode the original console-paste Lambda workflow risked, avoided here from the start rather than retrofitted).
- **Why flatten `generationmix` into fixed columns instead of keeping it as a nested list:** the raw API returns each region's fuel mix as a list of `{"fuel": ..., "perc": ...}` pairs. A flat row — one column per fuel type (`wind_pct`, `gas_pct`, and so on) — is what SQL joins, `GROUP BY`, and window functions expect in Phase 5, and what a BigQuery external table can read directly without extra unnesting logic. Deciding this shape is Phase 3's job specifically, in keeping with the raw-zone-holds-everything-unmodified / curated-zone-holds-what's-actually-useful split from Phase 2.
- **Why cast every column explicitly rather than trust whatever pandas infers:** a single malformed or missing reading (a `null` forecast, a missing fuel type) can otherwise silently turn an entire column's dtype into a generic, harder-to-query "object" type instead of leaving one clean `NaN`/`NaT` in that one row. Explicit casting turns a data-quality problem into a visible missing value instead of an invisible one.
- **Why avoid `s3fs`:** pandas/pyarrow can write straight to an `s3://...` path if `s3fs` is installed, which would have been the shorter script — but it's one more third-party dependency to install at job startup (via `--additional-python-modules`) for something `boto3`, already built into every Glue Python Shell job, does perfectly well: write the partitioned Parquet files locally in the job's temp storage, then upload each one with a plain `s3.upload_file()` call. Fewer moving parts at job startup for the same result.

### How

**1. The transform job's own code and deploy config already live in your repo.** `transform/glue_jobs/clean_neso_data.py` is the actual transform logic — 📝 open it in VS Code and read it through before deploying, same habit as `handler.py` in Phase 2. Alongside it, `infra/` gained three new files: `neso_transform_glue_config.json` (the job's settings — name, role name, script location both locally and in S3, DPU tier, and the raw/curated S3 prefixes it reads from and writes to), `neso_transform_trust_policy.json` (trusts `glue.amazonaws.com`, same shape as the other trust policies), and `deploy_glue_transform.py` (the deploy script). Two existing files also changed: `neso_ingest_state_machine.json` now defines a second state (`RunNesoTransformGlueJob`, chained after the Lambda invoke — see Why above), and `neso_ingest_stepfunctions_config.json` gained a `glue_job_name` field so the Step Functions deploy script can build the Glue job's ARN.

**2. Check `infra/neso_transform_glue_config.json` before deploying.** `raw_s3_bucket`/`curated_s3_bucket` should match the bucket you created in Phase 2 — since this project keeps raw and curated data in the same bucket under different prefixes (`raw/neso-demand/` vs. `curated/neso-demand/`) rather than provisioning a second bucket, there's nothing new to create here, just confirm the bucket name matches.

**3. Deploy the Glue job.**
🖥️ **Terminal** (`.venv` activated, inside `gridwatch`):
```
python infra/deploy_glue_transform.py
```
This creates the job's execution role (the AWS-managed `AWSGlueServiceRole` policy, plus an inline policy scoped to read the raw prefix, write the curated prefix, and read the job's own script location), uploads `clean_neso_data.py` to S3, then creates the Glue job itself pointed at that S3 location. You'll see `Created IAM role...`, `Uploaded transform/glue_jobs/clean_neso_data.py...`, `Created Glue job...` printed as it runs.

**From now on, every time you change `clean_neso_data.py`:** save the file, then just re-run `python infra/deploy_glue_transform.py` again — it re-uploads the script and updates the job in place, the same edit-deploy loop as the Lambda.

**4. Test the Glue job on its own, before wiring it into the full workflow.**
🌐 **Browser (AWS Console):**
1. Search "Glue" → **ETL jobs** → click `gridwatch-neso-transform`
2. Click **Run** (top-right)
3. Click the **Runs** tab and watch until the status shows **Succeeded** — a Python Shell job has real startup time, often 30-90 seconds, even though the transform logic itself runs in a couple of seconds once it's up
4. Check S3: your bucket → `curated/neso-demand/` → you should see a `reading_date=<today's date>/` folder containing a `.parquet` file

**5. Deploy the updated Step Functions workflow, chaining the two steps together.**
🖥️ **Terminal:**
```
python infra/deploy_stepfunctions.py
```
Same command you've run before — this time it updates the state machine's definition (picking up the new second state) and widens its role to the new Lambda-plus-Glue permissions (see Why above). You'll see `Attached '...-invoke-lambda-and-glue'...` and `Updated existing state machine...` in the output, confirming both changes landed.

**6. Test the full chain end to end.**
🌐 **Browser (AWS Console):**
1. Search "Step Functions" → **State machines** → `gridwatch-neso-ingestion` (check the region selector shows **eu-west-2 (London)** first)
2. **Start execution** → leave the input as `{}` → **Start execution**
3. Watch the graph: `InvokeNesoIngestLambda` turns green first, then `RunNesoTransformGlueJob` — the second state takes longer to complete than the first, for the same Glue startup-time reason as Step 4
4. Once the whole execution shows **Succeeded**, check `curated/neso-demand/reading_date=<today>/` in S3 again — you should see a *second* Parquet file alongside the one from Step 4, confirming the whole chain (Step Functions → Lambda → S3 → Glue → S3) ran on its own, not just the piece you'd already tested manually

**7. Verify end to end, then commit.** Wait for tomorrow's 9am scheduled run (or trigger it manually the same way as Step 6 to confirm sooner), then commit `transform/` and `infra/` to a feature branch and merge — same pattern as every phase before this one.

**An honesty note for later:** you won't have access to real substation capacity thresholds (that's internal DNO data), so "stress" in this project should be framed as a *relative* measure — e.g. top-percentile load periods for a given substation/region — rather than claiming to know true remaining capacity. Say this explicitly in your write-up; it reads as more credible, not less.

**Definition of done:** curated, partitioned Parquet landing in S3 automatically every day, as the second step of the same Step Functions workflow from Phase 2, with the transform's code and AWS configuration (IAM role, DPU tier, job settings) version-controlled in the repo and deployed with a repeatable `python infra/deploy_glue_transform.py` rather than clicked together in the console. (Registering the curated schema in the Glue Data Catalog — useful once you're querying it directly via Athena — is deliberately left for later, only if that becomes something you actually need; Phase 4 loads the curated data into BigQuery directly rather than through the Data Catalog.)

### What — argument and concept reference

- **DPU (Data Processing Unit)** — Glue's unit of compute power (already introduced in Part 2's cost breakdown). Python Shell jobs can only be set to **0.0625** or **1** DPU — a much narrower choice than Spark ETL jobs, which scale across many workers; 0.0625 is the smallest and cheapest option, and comfortably enough for this job's actual workload.
- **`GlueVersion`** — determines which Python version and which libraries come pre-installed in a Python Shell job's environment. `"3.0"` here gives Python 3.9 with `pandas`, `numpy`, and `boto3` pre-installed — but notably **not** `pyarrow`, which is why the deploy script requests it separately (see `--additional-python-modules` below).
- **`--additional-python-modules`** — a Glue job parameter (set in `deploy_glue_transform.py`'s `DefaultArguments`) that pip-installs extra packages when the job starts, for anything not already part of the `GlueVersion`'s pre-installed set. Used here to add `pyarrow`, needed for `pandas`/`pyarrow` to write Parquet files.
- **Hive-style partitioning** — the `reading_date=2026-08-17/` folder-naming convention `pyarrow.parquet.write_to_dataset(..., partition_cols=[...])` produces. Naming partition folders `<column>=<value>` (rather than just `2026-08-17/`) is a widely recognized convention that lets Athena, a Glue Crawler, or a BigQuery external table automatically discover which partitions exist and skip straight to the relevant one for a filtered query, instead of you registering each date by hand.
- **`.sync` service integration** — a suffix Step Functions recognizes on certain AWS service ARNs (`arn:aws:states:::glue:startJobRun.sync` here) meaning "wait for this to actually finish, not just start, before treating the state as complete." Without it, a `Task` state calling `glue:startJobRun` (no `.sync`) would succeed the instant the Glue API confirmed the job had *started* — regardless of whether it went on to actually finish or fail.
- **`AWSGlueServiceRole`** — an AWS-managed policy (like `AWSLambdaBasicExecutionRole` for Lambda) granting the baseline permissions any Glue job needs to run at all and write its own CloudWatch Logs. `deploy_glue_transform.py` attaches it automatically, on top of the job's own narrowly-scoped inline S3 policy.
- **`get_job` / `create_job` / `update_job`** — the boto3 Glue methods `deploy_glue_transform.py` uses to check whether the job already exists (an exception means "not found yet") and switch between creating it fresh or updating it in place — the same create-or-update pattern used everywhere else in this project.
- **`s3.upload_file()`** — the boto3 S3 method used both to push `clean_neso_data.py` up to its script location before deploying the job, and inside the job itself to push each finished Parquet partition file up to the curated zone — ordinary file uploads, doing the job a heavier `s3fs`-based approach would do less transparently.

## Phase 4 — Load into BigQuery (star schema)

### Why

- **Why this phase is genuinely different from Phases 1-3:** every AWS resource so far stayed inside one cloud — the whole question was "deploy this correctly," never "how does data physically get from A to B." Phase 4 needs data to cross from AWS (S3) into GCP (BigQuery), and the two clouds don't share storage — there's no path that doesn't involve an explicit hop through Google Cloud Storage (GCS) first, since BigQuery can only load from GCS, not directly from S3.
- **Why a plain script over BigQuery Omni or GCP's Storage Transfer Service:** both real alternatives, both rejected on the same cost/complexity grounds that shaped the Glue-vs-Spark decision in Phase 3. BigQuery Omni would let BigQuery query the S3 Parquet in place, with no data movement at all — elegant, but it requires BigQuery Enterprise/Enterprise Plus edition, real ongoing cost outside this project's always-free approach. GCP's Storage Transfer Service would pull from S3 on a schedule with no custom code — but it needs your AWS access keys stored as a GCP credential (a second long-lived cross-cloud secret, on top of the one this phase already needed) and has its own scheduling/cost model, for not much benefit at this data volume. A script following the same config-plus-deploy-script habit as everything else in this project was the better fit.
- **Why the destination table is called `fact_carbon_intensity_readings`, not the `fact_network_readings` this section originally sketched:** that draft was written before any real data existed, and proposed a `demand_or_consumption` column the Carbon Intensity API doesn't actually provide — only carbon intensity and generation mix. Naming the table for what it actually contains, rather than leaving a stale aspirational name in place, matches the same "the real data is the source of truth, not the plan" principle Phase 3's actual column set already followed.
- **Why `relative_load_percentile` isn't a stored column:** it's a derived measure — a reading's value relative to other readings — which belongs in Phase 5's SQL, computed at query time, not duplicated as a stale stored value that would need recomputing every time new data lands.
- **Why the bridge script needed a two-stage build (manual first, then automated) rather than going straight to automation:** the manual version (`warehouse/load_curated_to_bigquery.py`, run from your own laptop) let the actual cross-cloud logic — copy from S3, re-upload to GCS, load into BigQuery — get proven correct against real data with fast iteration and a human reading every error message. Automating it as a Lambda afterward meant the *logic* was already trusted, and the remaining work was purely "how does a cloud-hosted job authenticate to a second cloud" — a cleanly separated, genuinely different problem, easier to solve on its own than tangled up with debugging the transform logic at the same time.
- **Why the manual script has no IAM role, unlike every other deploy script:** Lambda, Step Functions, and Glue all needed a role because the resource itself runs *in the cloud* and needs its own identity. The manual script runs on your own laptop, using identities you already have — your AWS IAM user (`aws configure`, Part 1.1) for S3, and Google's Application Default Credentials (a separate login from the `gcloud` CLI's own — see the "gcloud has two logins" note below) for GCS and BigQuery.
- **Why the automated Lambda authenticates via a service account key in Secrets Manager, not Workload Identity Federation:** WIF is the more modern, keyless approach — no long-lived secret ever stored anywhere, since the Lambda would exchange its own short-lived AWS credentials for a short-lived GCP token at request time. It's genuinely the better long-term answer, and worth knowing exists. It was set aside here for a simpler, faster-to-get-working first version: a service account key, stored in AWS Secrets Manager, fetched by the Lambda at runtime and never written to disk. The trade-off is real and worth naming plainly — a static key is a long-lived credential that works until manually rotated, even if it leaked. (Notably, Google itself now defaults newer projects to *blocking* key creation entirely, specifically to push people toward WIF — see the troubleshooting note below for how that actually played out.)
- **Why the Lambda's own deploy script is more complex than the earlier two Lambda deploys:** `deploy_neso_ingest.py` only ever zipped `handler.py` itself, since Lambda's runtime already includes everything that Lambda needed (`boto3`, the standard library). This Lambda also needs `google-cloud-storage` and `google-cloud-bigquery`, which aren't part of any Lambda runtime — so `deploy_bigquery_load_lambda.py` has to `pip install` them into a build folder *targeting Lambda's own Linux environment specifically* (not whatever OS you're running the deploy script on) before zipping anything, and then check whether the result is small enough to upload directly (Lambda's inline-upload limit is 50MB compressed) or needs uploading to S3 first instead (a much higher limit applies when Lambda loads code from S3).

### How

**Loading Phase 1's mock CSVs** — unchanged from the original plan, and independent of everything else in this phase:

**1.** 🖥️ **Terminal** (`.venv` activated, inside `gridwatch`), create the tables with explicit schemas (safer than letting BigQuery guess types from a CSV):
```
bq mk --table your-project-id:gridwatch.accounts account_id:INTEGER,account_name:STRING,region_id:INTEGER,region_name:STRING,contract_tier:STRING,contract_start_date:DATE,renewal_date:DATE,churn_date:DATE,properties_served:INTEGER
bq mk --table your-project-id:gridwatch.users user_id:INTEGER,account_id:INTEGER,role:STRING,signup_date:DATE
bq mk --table your-project-id:gridwatch.usage_events user_id:INTEGER,event_timestamp:DATE,event_type:STRING
```
(the dataset itself, `gridwatch`, gets created automatically the first time either the manual or automated load script runs — see below — so there's no separate `bq mk --dataset` step needed if you do this phase in the order below)

**2. Load the CSVs:**
```
bq load --source_format=CSV --skip_leading_rows=1 your-project-id:gridwatch.accounts mock_data/output/accounts.csv
bq load --source_format=CSV --skip_leading_rows=1 your-project-id:gridwatch.users mock_data/output/users.csv
bq load --source_format=CSV --skip_leading_rows=1 your-project-id:gridwatch.usage_events mock_data/output/usage_events.csv
```

**3. Verify the join key:**
```
bq query --use_legacy_sql=false 'SELECT region_id, COUNT(*) AS accounts FROM `your-project-id.gridwatch.accounts` GROUP BY region_id ORDER BY region_id'
```
All 14 `region_id` values should appear, same set `fact_carbon_intensity_readings` uses below — confirming Phase 1's mock data and the real NESO data can actually be joined in Phase 5.

**Bridging the real curated data — manual version first:**

**4. Set up GCP tooling**, if this is the first time you've actually used it in this project:
- Install the two Python packages the bridge script needs: 🖥️ **Terminal** — `pip install google-cloud-storage google-cloud-bigquery`
- **`gcloud` has two separate logins, and you need both.** `gcloud auth login` authenticates the `gcloud` command-line tool itself (needed for commands like `gcloud projects list`). `gcloud auth application-default login` separately authenticates any Python code using Google's client libraries (needed for the script itself to run). Run both if you haven't already:
```
gcloud auth login
gcloud auth application-default login
```
- If `gcloud` itself isn't found at all, it's likely a PATH issue rather than a missing install — check `ls ~/google-cloud-sdk` first; if that folder exists, run `source "$HOME/google-cloud-sdk/path.zsh.inc"` to load it into your current terminal, then add that line to `~/.zshrc` so future terminal windows pick it up automatically.
- Find your project ID: `gcloud config get-value project`. If that comes back `(unset)`, list your projects with `gcloud projects list` and set one as default with `gcloud config set project YOUR_PROJECT_ID` — use the value under the `PROJECT_ID` column specifically, not `NAME` or `PROJECT_NUMBER`.

**5. Create a GCS bucket** to hold the bridged data (bucket names are globally unique, same rule as S3):
```
gcloud storage buckets create gs://gridwatch-curated-andy817 --project=YOUR_PROJECT_ID --location=europe-west2
```

**6.** 📝 **File — `warehouse/bigquery_load_config.json`:** set `gcp_project_id` and `gcs_bucket` to match what you just found/created.

**7. Run it:**
```
python warehouse/load_curated_to_bigquery.py
```
This copies today's curated Parquet partition from S3 to GCS, then loads it into BigQuery — creating the `gridwatch` dataset and the `fact_carbon_intensity_readings` table automatically on first run (Parquet files carry their own schema, so BigQuery reads column names and types straight from the file, no manual `bq mk --table` needed for this one).

**A schema bug this phase caught, worth knowing about even though it's already fixed:** the first attempt at this failed with *"The field specified for partitioning cannot be found in the schema"*, then, once fixed, *"...can only be of type TIMESTAMP, DATETIME, or DATE. The type found is: STRING."* Both were bugs in Phase 3's Glue script, only surfaced once Phase 4 tried to actually use the `reading_date` column: `pyarrow`'s own `write_to_dataset(..., partition_cols=[...])` strips the partition column out of each file once it's encoded in the folder name (fixed by writing each partition's file manually, keeping the column), and the column had been stored as a plain string rather than a real date value (fixed by removing an unnecessary `.astype(str)`). `transform/glue_jobs/clean_neso_data.py`, as currently in the repo, already has both fixes — mentioned here because it's a good example of a bug that couldn't have been caught by Phase 3 alone, since Phase 3's own "definition of done" (a Parquet file lands in S3) doesn't test whether a *different* system can actually make use of what's in it.

**8. Sanity-check the loaded data**, the BigQuery equivalent of Phase 1's region-spread check:
```sql
SELECT COUNT(*) AS total_rows,
  COUNTIF(ABS(biomass_pct + coal_pct + imports_pct + gas_pct + nuclear_pct + other_pct + hydro_pct + solar_pct + wind_pct - 100) > 0.5) AS rows_off_by_more_than_0_5pct
FROM `your-project-id.gridwatch.fact_carbon_intensity_readings`
```
`rows_off_by_more_than_0_5pct` should come back 0 — a small tolerance rather than exact-100 equality, since the source API rounds each fuel percentage to one decimal place, and summing several independently-rounded values can drift a few tenths either side of exactly 100 without anything actually being wrong.

**Automating it — a third Lambda, chained onto the existing workflow:**

**9. One-time setup: a GCP service account, and its key in AWS Secrets Manager.** 🖥️ **Terminal** (replace `YOUR_PROJECT_ID` throughout):
```
gcloud iam service-accounts create gridwatch-loader --display-name="GridWatch BigQuery Loader" --project=YOUR_PROJECT_ID
gcloud storage buckets add-iam-policy-binding gs://gridwatch-curated-andy817 --member="serviceAccount:gridwatch-loader@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:gridwatch-loader@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/bigquery.jobUser"
```
For the dataset's own edit access, use the BigQuery console's **Sharing** button on the `gridwatch` dataset → **Add principal** → the service account's email → role **BigQuery Data Editor** — the newer `bq add-iam-policy-binding` command for datasets is gated behind a Google allowlist on many projects (it was on this one), so the console's own sharing UI is the more reliable path.

**Note on GCS roles:** `roles/storage.objectAdmin`, not the narrower `roles/storage.objectCreator` — the daily job re-runs against the same file each day (see Phase 3's fixed-filename change), so it needs to *overwrite* an existing object, not just create new ones. GCS treats overwriting as requiring delete permission on the previous version, which `objectCreator` deliberately doesn't grant.

**10. Generate the key and store it in Secrets Manager.** If `gcloud iam service-accounts keys create ...` fails with `FAILED_PRECONDITION: Key creation is not allowed on this service account` (a real, increasingly common default on newer GCP projects, specifically meant to push you toward Workload Identity Federation instead), try overriding the **Disable service account key creation** organization policy for your project via the console first — if that's not available to you either (locked above your project, not uncommon on personal accounts), generate the key from the console instead: IAM & Admin → **Service Accounts** → the account → **Keys** tab → **Add Key** → **Create new key** → JSON. Wherever it downloads to:
```
aws secretsmanager create-secret --name gridwatch/gcp-loader-key --secret-string file://path/to/the-downloaded-key.json --region eu-west-2
rm path/to/the-downloaded-key.json
```
Delete the local copy immediately after it's in Secrets Manager — the fewer places a credential like this exists, the smaller the blast radius if your laptop were ever compromised. (`.gitignore` also has a pattern catching common key filenames, as a second layer of protection in case one ever ends up inside the repo folder by accident.)

**11.** 📝 **File — `infra/neso_bigquery_load_lambda_config.json`:** set `gcp_project_id` to your real project ID.

**12. Deploy the Lambda:**
```
python infra/deploy_bigquery_load_lambda.py
```
Slower than the earlier Lambda deploys — it's genuinely downloading `google-cloud-bigquery` and its dependencies before it can package anything.

**13. Test it standalone** before wiring it in: 🌐 **Browser** → Lambda console → `gridwatch-bigquery-load` → **Test** tab → any event name, default `{}` body → **Test**. Check the response for `rows_loaded`.

**14. Wire it into the workflow:**
```
python infra/deploy_stepfunctions.py
```
This updates the state machine to a third state (`LoadCuratedIntoBigQuery`, chained after the Glue step) and widens its role to invoke both Lambdas, on top of the Glue permissions from Phase 3.

**15. Test the full three-step chain:** Step Functions console → `gridwatch-neso-ingestion` → **Start execution** → watch `InvokeNesoIngestLambda` → `RunNesoTransformGlueJob` → `LoadCuratedIntoBigQuery` all turn green in order.

**16. Verify end to end, then commit.** Check BigQuery for the new rows, then commit `warehouse/`, `ingestion/lambdas/neso_bigquery_load/`, and the changed `infra/` files to a feature branch and merge.

**Definition of done:** all three Phase 1 tables loaded into BigQuery with the `region_id` join key confirmed clean, real NESO data landing in `fact_carbon_intensity_readings` automatically every day as the third step of the same Step Functions workflow from Phases 2-3, and both the manual bridge script and its automated Lambda equivalent version-controlled and deployed the same repeatable way as everything else in this project.

### What — argument and concept reference

- **Application Default Credentials (ADC)** — the credential set Google's client libraries (as opposed to the `gcloud` CLI itself) look for automatically. `gcloud auth application-default login` sets these up; a genuinely separate login step from `gcloud auth login`, which only authenticates the CLI.
- **GCP service account** — GCP's equivalent of an AWS IAM role: a non-human identity that code can act as, with its own permissions, distinct from your own Google account.
- **Service account key** — a long-lived credential (a JSON file) that lets code authenticate *as* a service account without a live login flow. The thing Workload Identity Federation exists to make unnecessary.
- **Workload Identity Federation (WIF)** — lets GCP trust an external identity (here, an AWS IAM role) directly, so a workload exchanges its own short-lived credentials for a short-lived GCP token at runtime, with no static key ever created or stored. The road not taken in this phase, deliberately, in favor of a simpler first version — worth revisiting later.
- **`roles/storage.objectCreator` vs. `roles/storage.objectAdmin`** — GCS permission tiers. Creator can only write new objects; overwriting an existing one needs delete permission on the old version too, which only Admin (or a custom role including `storage.objects.delete`) grants.
- **`roles/bigquery.dataEditor` vs. `roles/bigquery.jobUser`** — dataEditor covers reading/writing data within a specific dataset; jobUser is what actually lets an identity *run* a query or load job at all, and — unlike dataEditor — has no dataset-scoped equivalent, only project-level.
- **BigQuery dataset ACLs vs. Cloud IAM** — BigQuery historically managed dataset-level access through its own ACL system (what the console's **Sharing** button edits), predating and still coexisting with Cloud IAM's newer `bq add-iam-policy-binding` equivalent — the latter isn't uniformly available on every project yet.
- **`s3:ListBucket` vs. `s3:GetObject`** — two separately-scoped S3 permissions with different required `Resource` shapes: `GetObject` needs an object-level ARN (`bucket/key`), but `ListBucket` — what a paginated listing call like `list_objects_v2` actually uses — needs the *bucket-level* ARN (no key), optionally narrowed with an `s3:prefix` condition. Granting only the first is a common, easy-to-miss gap when a script both lists and reads objects.
- **Lambda deployment package size limits** — 50MB compressed for a direct/inline upload; up to 250MB unzipped when the package is loaded from S3 instead. `deploy_bigquery_load_lambda.py` checks the built zip's size and switches between the two automatically.
- **`pip install --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all:`** — downloads prebuilt wheels for Lambda's own Linux environment regardless of what OS the deploy script itself runs on. Without this, `pip` installs packages built for your own machine, which fail to import once uploaded to Lambda.
- **`WRITE_APPEND`** — the BigQuery load disposition used here: each run adds its rows rather than replacing the table's contents. Correct for a growing time-series fact table, but means re-running a load for the same day twice appends that day's rows twice — an accepted, documented limitation rather than a solved problem, matched to what this project actually needs rather than over-engineered.

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
