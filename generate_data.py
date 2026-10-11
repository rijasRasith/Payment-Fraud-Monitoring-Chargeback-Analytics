import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import os

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 9, 30)

REASON_CODES = {
    "VISA_10.4": "Other Fraud - Card Absent",
    "VISA_10.5": "Visa Fraud Monitoring Program",
    "VISA_12.1": "Late Presentment",
    "VISA_12.6": "Duplicate Processing",
    "MC_4837": "No Cardholder Authorization",
    "MC_4853": "Cardholder Dispute",
    "MC_4855": "Non-Receipt of Merchandise",
    "MC_4863": "Cardholder Does Not Recognize",
}

FRAUD_REASON_CODES = ["VISA_10.4", "VISA_10.5", "MC_4837", "MC_4863"]
TECHNICAL_REASON_CODES = ["VISA_12.1", "VISA_12.6", "MC_4853", "MC_4855"]

CHARGEBACK_STAGES = [
    "retrieval_request",
    "first_chargeback",
    "representment",
    "pre_arbitration",
    "arbitration",
]

HIGH_RISK_MERCHANT_IDS = [3, 7]


def random_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def generate_merchants(n=20):
    categories = [
        "Electronics", "Travel", "Retail", "Food & Beverage",
        "Digital Goods", "Health & Beauty", "Gambling", "Crypto Exchange",
        "Subscription Services", "Gaming",
    ]
    records = []
    for i in range(1, n + 1):
        is_high_risk = i in HIGH_RISK_MERCHANT_IDS
        category = random.choice(["Gambling", "Crypto Exchange"]) if is_high_risk else random.choice(categories)
        records.append({
            "merchant_id": i,
            "merchant_name": fake.company(),
            "category": category,
            "country": fake.country_code(),
            "mcc_code": random.randint(5000, 7999),
            "onboarded_date": fake.date_between(start_date="-5y", end_date="-1y").isoformat(),
            "is_high_risk": int(is_high_risk),
        })
    return pd.DataFrame(records)


def generate_customers(n=500):
    records = []
    for i in range(1, n + 1):
        country = fake.country_code()
        records.append({
            "customer_id": i,
            "name": fake.name(),
            "email": fake.email(),
            "country": country,
            "card_type": random.choice(["Visa", "Mastercard", "Visa", "Mastercard", "Amex"]),
            "created_at": fake.date_between(start_date="-3y", end_date="-6m").isoformat(),
        })
    return pd.DataFrame(records)


def generate_transactions(merchants_df, customers_df, n_normal=4000):
    records = []
    txn_id = 1

    for _, row in merchants_df.iterrows():
        merchant_id = row["merchant_id"]
        is_high_risk = bool(row["is_high_risk"])
        n_per_merchant = random.randint(150, 250) if not is_high_risk else random.randint(400, 600)

        for _ in range(n_per_merchant):
            customer_id = random.randint(1, len(customers_df))
            txn_date = random_date(START_DATE, END_DATE)
            amount = round(random.lognormvariate(4.2, 0.9), 2)
            status = random.choices(
                ["approved", "declined", "refunded"],
                weights=[0.78, 0.18, 0.04] if not is_high_risk else [0.60, 0.32, 0.08],
            )[0]
            ip_country = fake.country_code()
            billing_country = customers_df.loc[customers_df["customer_id"] == customer_id, "country"].values[0]
            location_mismatch = int(ip_country != billing_country)

            records.append({
                "transaction_id": txn_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "amount": amount,
                "currency": "USD",
                "status": status,
                "txn_datetime": txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                "hour_of_day": txn_date.hour,
                "ip_country": ip_country,
                "billing_country": billing_country,
                "location_mismatch": location_mismatch,
                "is_fraud": 0,
            })
            txn_id += 1

    fraud_patterns = _inject_fraud_patterns(merchants_df, customers_df, txn_id)
    records.extend(fraud_patterns["records"])
    txn_id = fraud_patterns["next_id"]

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    df["transaction_id"] = range(1, len(df) + 1)
    return df


def _inject_fraud_patterns(merchants_df, customers_df, start_id):
    records = []
    txn_id = start_id

    for burst_num in range(15):
        customer_id = random.randint(1, len(customers_df))
        merchant_id = random.randint(1, len(merchants_df))
        base_time = random_date(START_DATE, END_DATE)
        burst_size = random.randint(5, 12)
        for j in range(burst_size):
            txn_time = base_time + timedelta(minutes=j * random.randint(1, 4))
            records.append({
                "transaction_id": txn_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "amount": round(random.uniform(50, 300), 2),
                "currency": "USD",
                "status": "approved",
                "txn_datetime": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                "hour_of_day": txn_time.hour,
                "ip_country": fake.country_code(),
                "billing_country": customers_df.loc[customers_df["customer_id"] == customer_id, "country"].values[0],
                "location_mismatch": 1,
                "is_fraud": 1,
            })
            txn_id += 1

    for _ in range(60):
        merchant_id = random.choice(HIGH_RISK_MERCHANT_IDS)
        customer_id = random.randint(1, len(customers_df))
        txn_date = random_date(START_DATE, END_DATE)
        records.append({
            "transaction_id": txn_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "amount": round(random.uniform(2000, 15000), 2),
            "currency": "USD",
            "status": "approved",
            "txn_datetime": txn_date.strftime("%Y-%m-%d %H:%M:%S"),
            "hour_of_day": txn_date.hour,
            "ip_country": fake.country_code(),
            "billing_country": customers_df.loc[customers_df["customer_id"] == customer_id, "country"].values[0],
            "location_mismatch": 1,
            "is_fraud": 1,
        })
        txn_id += 1

    for _ in range(80):
        merchant_id = random.choice(HIGH_RISK_MERCHANT_IDS)
        customer_id = random.randint(1, len(customers_df))
        txn_date = random_date(START_DATE, END_DATE).replace(hour=random.randint(2, 5))
        records.append({
            "transaction_id": txn_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "amount": round(random.uniform(100, 800), 2),
            "currency": "USD",
            "status": "approved",
            "txn_datetime": txn_date.strftime("%Y-%m-%d %H:%M:%S"),
            "hour_of_day": txn_date.hour,
            "ip_country": fake.country_code(),
            "billing_country": customers_df.loc[customers_df["customer_id"] == customer_id, "country"].values[0],
            "location_mismatch": 1,
            "is_fraud": 1,
        })
        txn_id += 1

    for customer_id in random.sample(range(1, 501), 30):
        merchant_id = random.randint(1, 20)
        base_time = random_date(START_DATE, END_DATE)
        for attempt in range(random.randint(4, 8)):
            txn_time = base_time + timedelta(minutes=attempt * 2)
            status = "declined" if attempt < (random.randint(3, 6)) else "approved"
            records.append({
                "transaction_id": txn_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "amount": round(random.uniform(20, 200), 2),
                "currency": "USD",
                "status": status,
                "txn_datetime": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                "hour_of_day": txn_time.hour,
                "ip_country": fake.country_code(),
                "billing_country": customers_df.loc[customers_df["customer_id"] == customer_id, "country"].values[0],
                "location_mismatch": 1,
                "is_fraud": 1 if status == "approved" else 0,
            })
            txn_id += 1

    return {"records": records, "next_id": txn_id}


def generate_refunds(transactions_df):
    refunded_txns = transactions_df[transactions_df["status"] == "refunded"].copy()
    records = []
    for _, txn in refunded_txns.iterrows():
        txn_date = datetime.strptime(txn["txn_datetime"], "%Y-%m-%d %H:%M:%S")
        refund_date = txn_date + timedelta(days=random.randint(1, 14))
        records.append({
            "refund_id": len(records) + 1,
            "transaction_id": int(txn["transaction_id"]),
            "merchant_id": int(txn["merchant_id"]),
            "amount": round(txn["amount"] * random.uniform(0.8, 1.0), 2),
            "refund_date": refund_date.strftime("%Y-%m-%d"),
            "reason": random.choice(["customer_request", "duplicate", "not_received", "defective"]),
            "status": "completed",
        })
    return pd.DataFrame(records)


def generate_chargebacks(transactions_df, merchants_df):
    fraud_txns = transactions_df[
        (transactions_df["is_fraud"] == 1) & (transactions_df["status"] == "approved")
    ].copy()
    normal_approved = transactions_df[
        (transactions_df["is_fraud"] == 0) & (transactions_df["status"] == "approved")
    ].sample(n=min(80, len(transactions_df[transactions_df["is_fraud"] == 0])), random_state=SEED)

    chargeback_pool = pd.concat([fraud_txns.sample(frac=0.65, random_state=SEED), normal_approved])
    chargeback_pool = chargeback_pool.sample(frac=1, random_state=SEED).reset_index(drop=True)

    records = []
    for idx, txn in chargeback_pool.iterrows():
        txn_date = datetime.strptime(txn["txn_datetime"], "%Y-%m-%d %H:%M:%S")
        dispute_date = txn_date + timedelta(days=random.randint(5, 45))

        is_fraud_txn = bool(txn["is_fraud"])
        if is_fraud_txn:
            reason_code = random.choice(FRAUD_REASON_CODES)
        else:
            reason_code = random.choice(TECHNICAL_REASON_CODES)

        max_stage_idx = random.randint(1, 4)
        current_stage = CHARGEBACK_STAGES[max_stage_idx]

        if max_stage_idx == 1:
            outcome = random.choices(["lost", "pending"], weights=[0.7, 0.3])[0]
        elif max_stage_idx == 2:
            outcome = random.choices(["won", "lost", "pending"], weights=[0.45, 0.40, 0.15])[0]
        elif max_stage_idx == 3:
            outcome = random.choices(["won", "lost", "pending"], weights=[0.25, 0.65, 0.10])[0]
        else:
            outcome = random.choices(["won", "lost"], weights=[0.15, 0.85])[0]

        stage_start = dispute_date
        for stage_idx in range(1, max_stage_idx + 1):
            stage_name = CHARGEBACK_STAGES[stage_idx]
            deadline_days = 30 if stage_idx <= 2 else 15
            deadline = stage_start + timedelta(days=deadline_days)
            is_final = stage_idx == max_stage_idx

            records.append({
                "chargeback_id": len(records) + 1,
                "transaction_id": int(txn["transaction_id"]),
                "merchant_id": int(txn["merchant_id"]),
                "customer_id": int(txn["customer_id"]),
                "disputed_amount": round(txn["amount"], 2),
                "reason_code": reason_code,
                "reason_description": REASON_CODES[reason_code],
                "chargeback_type": "fraud" if reason_code in FRAUD_REASON_CODES else "technical",
                "stage": stage_name,
                "stage_date": stage_start.strftime("%Y-%m-%d"),
                "deadline_date": deadline.strftime("%Y-%m-%d"),
                "outcome": outcome if is_final else "escalated",
                "is_final_stage": int(is_final),
                "arbitration_fee": round(random.uniform(500, 600), 2) if stage_name == "arbitration" else 0.0,
                "loss_amount": round(txn["amount"], 2) if (is_final and outcome == "lost") else 0.0,
                "is_fraud_transaction": int(is_fraud_txn),
            })
            stage_start = deadline + timedelta(days=random.randint(1, 5))

    df = pd.DataFrame(records)
    df["chargeback_id"] = range(1, len(df) + 1)
    return df


def main():
    merchants = generate_merchants(20)
    customers = generate_customers(500)
    transactions = generate_transactions(merchants, customers)
    refunds = generate_refunds(transactions)
    chargebacks = generate_chargebacks(transactions, merchants)

    merchants.to_csv(f"{DATA_DIR}/merchants.csv", index=False)
    customers.to_csv(f"{DATA_DIR}/customers.csv", index=False)
    transactions.to_csv(f"{DATA_DIR}/transactions.csv", index=False)
    refunds.to_csv(f"{DATA_DIR}/refunds.csv", index=False)
    chargebacks.to_csv(f"{DATA_DIR}/chargebacks.csv", index=False)

    print(f"Merchants:    {len(merchants):>6,}")
    print(f"Customers:    {len(customers):>6,}")
    print(f"Transactions: {len(transactions):>6,}")
    print(f"  of which fraud: {transactions['is_fraud'].sum():>4,}")
    print(f"Refunds:      {len(refunds):>6,}")
    print(f"Chargeback records: {len(chargebacks):>4,}")
    print(f"Unique chargeback cases: {chargebacks[chargebacks['is_final_stage']==1].shape[0]:>4,}")
    print("\nAll CSV files saved to ./data/")


if __name__ == "__main__":
    main()
