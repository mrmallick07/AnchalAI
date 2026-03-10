import pandas as pd
import numpy as np
import random

np.random.seed(42)
random.seed(42)

N = 1000  # number of women profiles

def generate_dataset(n):
    data = []

    for i in range(n):
        age = np.random.randint(16, 40)
        distance_to_phc_km = round(np.random.exponential(scale=12), 1)
        previous_pregnancies = np.random.randint(0, 6)
        attended_last_visit = np.random.choice([1, 0], p=[0.6, 0.4])
        household_income_level = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])  # 1=low, 2=mid, 3=high
        husband_support = np.random.choice([1, 0], p=[0.55, 0.45])
        literacy = np.random.choice([1, 0], p=[0.45, 0.55])  # 1=literate
        trimester_at_registration = np.random.choice([1, 2, 3], p=[0.3, 0.45, 0.25])
        harvest_season = np.random.choice([1, 0], p=[0.3, 0.7])
        asha_visits_so_far = np.random.randint(0, 5)

        # Dropout logic — based on real risk factors
        dropout_score = 0
        if age < 20: dropout_score += 2
        if distance_to_phc_km > 15: dropout_score += 2
        if attended_last_visit == 0: dropout_score += 3
        if household_income_level == 1: dropout_score += 1
        if husband_support == 0: dropout_score += 2
        if literacy == 0: dropout_score += 1
        if trimester_at_registration == 3: dropout_score += 2
        if harvest_season == 1: dropout_score += 1
        if asha_visits_so_far < 2: dropout_score += 1

        # Convert score to binary dropout label with some noise
        dropout_probability = min(dropout_score / 15, 0.95)
        dropout = int(np.random.random() < dropout_probability)

        data.append({
            "id": i + 1,
            "age": age,
            "distance_to_phc_km": distance_to_phc_km,
            "previous_pregnancies": previous_pregnancies,
            "attended_last_visit": attended_last_visit,
            "household_income_level": household_income_level,
            "husband_support": husband_support,
            "literacy": literacy,
            "trimester_at_registration": trimester_at_registration,
            "harvest_season": harvest_season,
            "asha_visits_so_far": asha_visits_so_far,
            "dropout": dropout
        })

    return pd.DataFrame(data)

df = generate_dataset(N)
df.to_csv("data/women_profiles.csv", index=False)
print(f"Dataset created: {len(df)} profiles")
print(f"Dropout rate: {df['dropout'].mean():.1%}")
print(df.head())
