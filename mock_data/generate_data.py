import random
from faker import Faker
from datetime import date, timedelta
from regions import REGIONS, REGION_PROFILE, CONSTRAINT_PRONE_REGIONS

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

def pull_toward_financial_year_start(d, earliest, latest, strength=0.35):
    """Nudges a date some fraction of the way toward the nearest 1 April
    (the UK utility financial year start, and the point DNOs' budget
    cycles reset) then clamps it back inside the allowed window.
    strength=0.35 means "35% of the way there" — enough to create a
    believable clustering of contract signings around the budget-cycle
    reset, without making every date suspiciously land on April 1st."""
    candidates = [date(d.year - 1, 4, 1), date(d.year, 4, 1), date(d.year + 1, 4, 1)]
    nearest_april = min(candidates, key=lambda c: abs((c - d).days))
    pulled = d + timedelta(days=int((nearest_april - d).days * strength))
    return max(earliest, min(latest, pulled))

TIERS = ["Basic", "Pro", "Enterprise"]
TIER_WEIGHTS = [0.5, 0.35, 0.15]

def generate_accounts(n=450):
    accounts = []
    today = date.today()
    earliest_start = today - timedelta(days=18 * 30)  # ~18 months ago
    latest_start = today - timedelta(days=30)          # ~1 month ago
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

# Winter months see more grid stress (cold-weather demand peaks), which
# plausibly means more logins/alerts — mirrors the real seasonal pattern
# NESO's own demand forecasting has to account for (see the Why section
# in the guide for the Average Cold Spell methodology this is loosely
# inspired by — not replicated, just borrowing the "winter matters more"
# principle).
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
