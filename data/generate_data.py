"""
AnchalAI — Realistic Synthetic Data Generator

Generates 500 women profiles with:
- Realistic Bengali/Hindi names
- Real-sounding rural village names
- Phone numbers, blood groups, estimated delivery dates
- Registration dates and last visit dates
- Outcome tracking: contacted, follow_up_status
- Clinically-informed dropout scoring
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

N = 500  # realistic catchment for 1 ASHA worker area

# ── Realistic Names ──────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Rina", "Sunita", "Parvati", "Meera", "Anita", "Lakshmi", "Priya",
    "Rekha", "Champa", "Durga", "Kavita", "Shanti", "Radha", "Usha",
    "Geeta", "Sumitra", "Anjali", "Bina", "Mala", "Tara", "Sita",
    "Aarti", "Mamta", "Renu", "Savita", "Kamla", "Saroj", "Nirmala",
    "Sarita", "Pushpa", "Kiran", "Babita", "Jyoti", "Pooja", "Neeta",
    "Guddi", "Pinki", "Suman", "Devi", "Rupa", "Bhavna", "Rachna",
    "Swati", "Archana", "Padma", "Manju", "Tulsi", "Gauri", "Lata",
    "Asha", "Kusum", "Seema", "Madhu", "Poonam", "Rita", "Kalyani",
    "Bharati", "Jharna", "Moumita", "Tanuja", "Ranjita", "Nilima",
    "Amrita", "Deepa", "Shobha", "Basanti", "Chhaya", "Malati",
    "Rukmini", "Damyanti", "Jamuna", "Phulwa", "Sakina", "Hasina",
    "Fatima", "Nasreen", "Rehana", "Shabnam", "Tabassum", "Zarina",
]

LAST_NAMES = [
    "Devi", "Mondal", "Das", "Ghosh", "Saha", "Roy", "Mandal",
    "Biswas", "Sarkar", "Pal", "Singh", "Kumari", "Mahato",
    "Halder", "Chatterjee", "Mukherjee", "Banerjee", "Bala",
    "Khatun", "Bibi", "Pramanik", "Mistry", "Oraon", "Tudu",
    "Murmu", "Hansda", "Soren", "Hembram", "Bauri", "Bag",
    "Dolai", "Malik", "Sheikh", "Molla", "Gazi", "Patra",
]

# ── Village Names (realistic rural Bengal / Jharkhand / Bihar) ────────────
VILLAGES = [
    "Gopalnagar", "Amtala", "Bhagwanpur", "Kalikapur", "Rautara",
    "Jhikira", "Beldanga", "Domkal", "Nalhati", "Suri",
    "Kalyani", "Basirhat", "Canning", "Kakdwip", "Patharpratima",
    "Hingalganj", "Gosaba", "Sandeshkhali", "Haroa", "Hasnabad",
    "Durgapur", "Ranaghat", "Krishnanagar", "Nabadwip", "Tehatta",
    "Kandi", "Jangipur", "Sagardighi", "Murshidabad", "Lalgola",
    "Rampurhat", "Dubrajpur", "Sainthia", "Bolpur", "Nanoor",
    "Purulia", "Raghunathpur", "Jhalda", "Manbazar", "Barabazar",
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
BLOOD_WEIGHTS = [0.22, 0.06, 0.33, 0.02, 0.28, 0.04, 0.04, 0.01]

# ── ASHA Workers ──────────────────────────────────────────────────────────
ASHA_WORKERS = [
    {"id": "ASHA-001", "name": "Sunita Devi", "block": "Block 4"},
    {"id": "ASHA-002", "name": "Mamta Roy", "block": "Block 4"},
    {"id": "ASHA-003", "name": "Kalyani Das", "block": "Block 7"},
    {"id": "ASHA-004", "name": "Renu Mondal", "block": "Block 7"},
    {"id": "ASHA-005", "name": "Jyoti Sarkar", "block": "Block 12"},
]


def generate_phone():
    """Generate a realistic Indian mobile number."""
    prefix = random.choice(["70", "73", "74", "75", "76", "77", "78", "79",
                             "80", "81", "82", "83", "84", "85", "86", "87",
                             "88", "89", "90", "91", "92", "93", "94", "95",
                             "96", "97", "98", "99"])
    return f"+91 {prefix}{random.randint(10000000, 99999999)}"


def generate_date_in_range(start, end):
    """Generate a random date between start and end."""
    delta = end - start
    random_days = random.randint(0, max(delta.days, 0))
    return start + timedelta(days=random_days)


def generate_dataset(n):
    today = datetime(2026, 3, 19)
    data = []
    used_names = set()

    for i in range(n):
        # Generate unique name
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            if name not in used_names:
                used_names.add(name)
                break

        village = random.choice(VILLAGES)
        phone = generate_phone()
        blood_group = np.random.choice(BLOOD_GROUPS, p=BLOOD_WEIGHTS)
        asha = random.choice(ASHA_WORKERS)

        # Demographics
        age = np.random.randint(16, 40)
        distance_to_phc_km = round(np.random.exponential(scale=12), 1)
        distance_to_phc_km = min(distance_to_phc_km, 55.0)  # cap at 55km
        previous_pregnancies = np.random.randint(0, 6)
        attended_last_visit = np.random.choice([1, 0], p=[0.6, 0.4])
        household_income_level = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])
        husband_support = np.random.choice([1, 0], p=[0.55, 0.45])
        literacy = np.random.choice([1, 0], p=[0.45, 0.55])
        trimester_at_registration = np.random.choice([1, 2, 3], p=[0.3, 0.45, 0.25])
        harvest_season = np.random.choice([1, 0], p=[0.3, 0.7])
        asha_visits_so_far = np.random.randint(0, 5)

        # Dates
        reg_offset = random.randint(30, 240)
        registration_date = today - timedelta(days=reg_offset)

        # EDD based on trimester at registration
        if trimester_at_registration == 1:
            edd = registration_date + timedelta(days=random.randint(168, 252))
        elif trimester_at_registration == 2:
            edd = registration_date + timedelta(days=random.randint(84, 168))
        else:
            edd = registration_date + timedelta(days=random.randint(14, 84))

        # Last visit date
        if attended_last_visit == 1:
            last_visit_date = today - timedelta(days=random.randint(1, 30))
        else:
            last_visit_date = today - timedelta(days=random.randint(30, 90))

        # Dropout scoring — clinically-informed
        dropout_score = 0
        if age < 20:
            dropout_score += 2
        if age > 35:
            dropout_score += 1
        if distance_to_phc_km > 15:
            dropout_score += 2
        if distance_to_phc_km > 30:
            dropout_score += 1
        if attended_last_visit == 0:
            dropout_score += 3
        if household_income_level == 1:
            dropout_score += 1
        if husband_support == 0:
            dropout_score += 2
        if literacy == 0:
            dropout_score += 1
        if trimester_at_registration == 3:
            dropout_score += 2
        if harvest_season == 1:
            dropout_score += 1
        if asha_visits_so_far < 2:
            dropout_score += 1
        if previous_pregnancies == 0:
            dropout_score += 1  # first-time mothers more likely to drop

        dropout_probability = min(dropout_score / 16, 0.95)
        dropout = int(np.random.random() < dropout_probability)

        # Outcome tracking (only some have been contacted)
        contacted = np.random.choice([1, 0], p=[0.3, 0.7])
        contact_date = ""
        follow_up_status = "pending"
        if contacted:
            contact_date = (today - timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
            follow_up_status = random.choice(["completed", "scheduled", "no_response"])

        data.append({
            "id": i + 1,
            "name": name,
            "village": village,
            "phone": phone,
            "age": age,
            "blood_group": blood_group,
            "distance_to_phc_km": distance_to_phc_km,
            "previous_pregnancies": previous_pregnancies,
            "attended_last_visit": attended_last_visit,
            "household_income_level": household_income_level,
            "husband_support": husband_support,
            "literacy": literacy,
            "trimester_at_registration": trimester_at_registration,
            "harvest_season": harvest_season,
            "asha_visits_so_far": asha_visits_so_far,
            "registration_date": registration_date.strftime("%Y-%m-%d"),
            "last_visit_date": last_visit_date.strftime("%Y-%m-%d"),
            "edd": edd.strftime("%Y-%m-%d"),
            "asha_worker_id": asha["id"],
            "asha_worker_name": asha["name"],
            "contacted": contacted,
            "contact_date": contact_date,
            "follow_up_status": follow_up_status,
            "dropout": dropout,
        })

    return pd.DataFrame(data)


if __name__ == "__main__":
    df = generate_dataset(N)
    df.to_csv("data/women_profiles.csv", index=False)
    print(f"✅ Dataset created: {len(df)} profiles")
    print(f"   Dropout rate: {df['dropout'].mean():.1%}")
    print(f"   Villages: {df['village'].nunique()}")
    print(f"   Contacted: {df['contacted'].sum()}")
    print(f"\n{df[['name', 'village', 'age', 'distance_to_phc_km', 'dropout']].head(10)}")
