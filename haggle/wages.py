"""Local wage data and fair price calculator.

Goal: Help travelers haggle to a fair price — one that respects the vendor's
time, materials, and livelihood — not the absolute minimum they can extract.

"Pay fair, not minimum."
"""

from typing import Optional

# Approximate minimum daily wages in USD (2025 estimates).
# Sources: ILO, World Bank, national labour ministry data.
WAGES: dict[str, dict] = {
    "Thailand":      {"daily_usd": 11.5,  "currency": "THB", "note": "Varies by province"},
    "Morocco":       {"daily_usd": 13.0,  "currency": "MAD"},
    "Turkey":        {"daily_usd": 20.0,  "currency": "TRY"},
    "India":         {"daily_usd": 5.5,   "currency": "INR", "note": "Varies by state & sector"},
    "Indonesia":     {"daily_usd": 9.0,   "currency": "IDR", "note": "Jakarta minimum"},
    "Mexico":        {"daily_usd": 14.5,  "currency": "MXN"},
    "Egypt":         {"daily_usd": 5.0,   "currency": "EGP"},
    "Vietnam":       {"daily_usd": 8.0,   "currency": "VND"},
    "Philippines":   {"daily_usd": 10.0,  "currency": "PHP"},
    "Cambodia":      {"daily_usd": 8.0,   "currency": "USD"},
    "Myanmar":       {"daily_usd": 4.5,   "currency": "MMK"},
    "Nepal":         {"daily_usd": 5.0,   "currency": "NPR"},
    "Sri Lanka":     {"daily_usd": 6.0,   "currency": "LKR"},
    "Kenya":         {"daily_usd": 6.5,   "currency": "KES"},
    "Tanzania":      {"daily_usd": 3.5,   "currency": "TZS"},
    "Ghana":         {"daily_usd": 5.0,   "currency": "GHS"},
    "Nigeria":       {"daily_usd": 4.0,   "currency": "NGN"},
    "South Africa":  {"daily_usd": 14.0,  "currency": "ZAR"},
    "Ethiopia":      {"daily_usd": 2.0,   "currency": "ETB"},
    "Guatemala":     {"daily_usd": 12.0,  "currency": "GTQ"},
    "Peru":          {"daily_usd": 11.0,  "currency": "PEN"},
    "Bolivia":       {"daily_usd": 7.0,   "currency": "BOB"},
    "Jordan":        {"daily_usd": 18.0,  "currency": "JOD"},
    "UAE":           {"daily_usd": 25.0,  "currency": "AED"},
    "Malaysia":      {"daily_usd": 18.0,  "currency": "MYR"},
    "Singapore":     {"daily_usd": 50.0,  "currency": "SGD"},
    "China":         {"daily_usd": 25.0,  "currency": "CNY", "note": "Shanghai minimum"},
    "Bangladesh":    {"daily_usd": 3.0,   "currency": "BDT"},
    "Pakistan":      {"daily_usd": 4.5,   "currency": "PKR"},
    "Brazil":        {"daily_usd": 15.0,  "currency": "BRL"},
    "Colombia":      {"daily_usd": 12.0,  "currency": "COP"},
}

# Estimated craft time in hours to produce one item.
# Deliberately conservative — most artisans are faster, but quality work takes time.
CRAFT_TIMES: dict[str, float] = {
    "silk scarf":         3.0,
    "pashmina shawl":     5.0,
    "leather bag":        8.0,
    "leather belt":       2.0,
    "handwoven textile":  12.0,
    "batik sarong":       4.0,
    "cotton shirt":       2.5,
    "tailored shirt":     4.0,
    "tailored suit":      16.0,
    "embroidered dress":  10.0,
    "wool blanket":       10.0,
    "keffiyeh":           2.0,
    "sari":               6.0,
    "ceramic bowl":       3.0,
    "pottery":            4.0,
    "wood carving":       6.0,
    "silver jewelry":     4.0,
    "evil eye bracelet":  1.0,
    "evil eye":           1.0,
    "papyrus art":        2.0,
    "carpet":             80.0,  # small rug
    "painting":           8.0,
    "metal lantern":      4.0,
    "brass tray":         5.0,
    "tea set":            3.0,
    "spice mix":          0.5,
    "beaded necklace":    2.0,
    "hand-painted tile":  3.0,
    "cotton galabeya":    3.0,
    "wood figurine":      4.0,
    "handicraft figurine": 4.0,
}

# Estimated material cost in USD to produce one item.
MATERIAL_COSTS: dict[str, float] = {
    "silk scarf":         2.0,
    "pashmina shawl":     3.5,
    "leather bag":        6.0,
    "leather belt":       1.5,
    "handwoven textile":  4.0,
    "batik sarong":       1.5,
    "cotton shirt":       1.5,
    "tailored shirt":     5.0,
    "tailored suit":      20.0,
    "embroidered dress":  6.0,
    "wool blanket":       7.0,
    "keffiyeh":           1.5,
    "sari":               4.0,
    "ceramic bowl":       1.0,
    "pottery":            1.5,
    "wood carving":       2.0,
    "silver jewelry":     4.0,
    "evil eye bracelet":  0.3,
    "evil eye":           0.3,
    "papyrus art":        0.5,
    "carpet":             25.0,
    "painting":           3.0,
    "metal lantern":      2.5,
    "brass tray":         3.0,
    "tea set":            3.0,
    "spice mix":          0.5,
    "beaded necklace":    0.8,
    "hand-painted tile":  1.5,
    "cotton galabeya":    2.5,
    "handicraft figurine": 1.5,
}


def _fuzzy_match(item: str, lookup: dict) -> Optional[str]:
    item_lower = item.lower().strip()
    if item_lower in lookup:
        return item_lower
    for key in lookup:
        if key in item_lower or item_lower in key:
            return key
    item_words = set(item_lower.split())
    best, best_score = None, 0
    for key in lookup:
        score = len(item_words & set(key.split()))
        if score > best_score:
            best, best_score = key, score
    return best if best_score > 0 else None


def get_fair_price(item: str, country: str) -> dict:
    """Calculate a fair price that sustains the vendor's livelihood.

    Returns context explaining the calculation so travelers understand
    the human cost behind what they're buying.
    """
    wage_data = WAGES.get(country, {"daily_usd": 10.0, "currency": "USD"})
    daily_wage = wage_data["daily_usd"]
    hourly_rate = daily_wage / 8.0

    time_key = _fuzzy_match(item, CRAFT_TIMES)
    craft_hours = CRAFT_TIMES.get(time_key, 2.0) if time_key else 2.0

    mat_key = _fuzzy_match(item, MATERIAL_COSTS)
    materials = MATERIAL_COSTS.get(mat_key, 2.0) if mat_key else 2.0

    labor_cost = craft_hours * hourly_rate

    # Fair price = materials + labor + 20% overhead (stall fees, tools, waste)
    fair_price = (materials + labor_cost) * 1.20

    # "Walk away" floor — the minimum that covers materials + basic labor
    floor_price = materials + (labor_cost * 0.6)

    days_of_work = craft_hours / 8.0

    return {
        "fair_price_usd": round(fair_price, 2),
        "floor_price_usd": round(floor_price, 2),
        "daily_wage_usd": daily_wage,
        "craft_hours": craft_hours,
        "labor_cost_usd": round(labor_cost, 2),
        "materials_usd": round(materials, 2),
        "country": country,
        "wage_note": wage_data.get("note"),
        "context": _build_context(item, country, daily_wage, craft_hours, fair_price, floor_price),
    }


def _build_context(
    item: str, country: str, daily_wage: float,
    craft_hours: float, fair_price: float, floor_price: float
) -> str:
    days = craft_hours / 8
    if days >= 1:
        time_str = f"~{days:.0f} day{'s' if days > 1 else ''}"
    else:
        time_str = f"~{craft_hours:.0f} hour{'s' if craft_hours > 1 else ''}"

    return (
        f"An artisan in {country} earns roughly ${daily_wage:.0f}/day. "
        f"This item takes {time_str} to make. "
        f"A fair price (covering materials, labour, and a small margin) is "
        f"around ${fair_price:.0f}+. "
        f"Below ${floor_price:.0f} and you're cutting into their basic costs."
    )


def get_wage_for_country(country: str) -> Optional[dict]:
    return WAGES.get(country)
