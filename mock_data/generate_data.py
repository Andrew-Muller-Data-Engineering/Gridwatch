import random
from faker import Faker
from datetime import date, timedelta
from regions import REGIONS

fake = Faker("en_GB")
random.seed(42)  # remove once you're happy with the shape of the data — see the What section below

def random_date_between(start, end):
    """A random calendar date between two dates (inclusive). Uses the
    already-seeded `random` module directly instead of Faker's relative
    date-string shorthand (e.g. "-18m") — that shorthand turned out not to
    resolve to a real window in the installed Faker version, so every date
    in the dataset was coming out identical. This is plain, dependable
    Python date math instead."""
    days_between = (end - start).days
    if days_between <= 0:
        return start
    return start + timedelta(days=random.randint(0, days_between))

TIERS = ["Basic", "Pro", "Enterprise"]
TIER_WEIGHTS = [0.5, 0.35, 0.15]

def generate_accounts(n=250):
    accounts = []
    today = date.today()
    earliest_start = today - timedelta(days=18 * 30)  # ~18 months ago
    latest_start = today - timedelta(days=30)          # ~1 month ago
    for i in range(n):
        region = random.choice(REGIONS)
        start = random_date_between(earliest_start, latest_start)
        renewal = start + timedelta(days=365)
        churned = random.random() < 0.15
        churn_date = random_date_between(start, today) if churned else None
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
LOW_ENGAGEMENT_REGIONS = {1, 2, 6, 7}  # North Scotland, South Scotland, N Wales/Mersey/Cheshire, South Wales

def generate_usage_events(users, accounts_by_id):
    events = []
    today = date.today()
    for user in users:
        account = accounts_by_id[user["account_id"]]
        base_events_per_week = 6
        if account["region_id"] in LOW_ENGAGEMENT_REGIONS:
            base_events_per_week *= 0.6
        for week in range(52):
            n_events = max(0, int(random.gauss(base_events_per_week, 2)))
            for _ in range(n_events):
                event_date = random_date_between(account["contract_start_date"], today)
                events.append({
                    "user_id": user["user_id"],
                    "event_timestamp": event_date,
                    "event_type": random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0],
                })
    return events

import pandas as pd

accounts = generate_accounts(250)
users = generate_users(accounts)
accounts_by_id = {a["account_id"]: a for a in accounts}
events = generate_usage_events(users, accounts_by_id)

pd.DataFrame(accounts).to_csv("mock_data/output/accounts.csv", index=False)
pd.DataFrame(users).to_csv("mock_data/output/users.csv", index=False)
pd.DataFrame(events).to_csv("mock_data/output/usage_events.csv", index=False)
print(f"Generated {len(accounts)} accounts, {len(users)} users, {len(events)} events")
