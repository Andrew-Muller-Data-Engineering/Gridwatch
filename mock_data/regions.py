# This is the official NESO region list — every other file in this project
# will import from here rather than typing region names by hand, so there's
# exactly one place that could ever be wrong, instead of many.
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

# Rough, illustrative weighting for account distribution and account "size"
# (properties_served), grounded in real regional customer counts where
# available (UK Power Networks serves ~8m customers combined across London,
# South East England and East England; SSEN serves ~3.9m combined across
# North Scotland and Southern England) and reasonable population-based
# tiers elsewhere, since exact per-DNO figures for every one of NESO's 14
# regions weren't readily available from a quick research pass. This is
# not a precise census — it's a defensible relative ordering: London/South
# East/East England (dense, high customer count) > the mid-size English
# regions > Wales/North East England/Scotland (sparser).
#
# population_weight: relative likelihood an account is placed in this region
#   (fed into random.choices — higher number = more accounts land here)
# properties_range: (min, max) properties a single account's operational
#   patch might realistically cover, in thousands — used to generate the
#   properties_served field per account
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
# burden: Scotland generates far more wind power than the transmission grid
# can currently export south, and GB-wide constraint payments (paying wind
# farms to switch off) hit roughly £1.8bn in 2025, up 20% on 2024, with
# Scotland accounting for most of that. Used in generate_data.py to bias
# product engagement lower in these regions specifically — a real,
# checkable-against-Phase-2-data pattern rather than an arbitrary one.
CONSTRAINT_PRONE_REGIONS = {1, 2}
