import os
import sys
import pandas as pd
import mysql.connector
from mysql.connector import errorcode

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": "fraud_analytics",
    "allow_local_infile": True,
}

DATA_DIR = "data"
SCHEMA_FILE = "sql/schema.sql"

TABLE_ORDER = ["merchants", "customers", "transactions", "refunds", "chargebacks"]


def get_connection_no_db():
    cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    return mysql.connector.connect(**cfg)


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS fraud_analytics "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print("  Database 'fraud_analytics' ready.")
    except mysql.connector.Error as err:
        print(f"  Error creating database: {err}")
        sys.exit(1)


def run_schema(connection, cursor):
    with open(SCHEMA_FILE, "r") as f:
        raw = f.read()

    statements = [s.strip() for s in raw.split(";") if s.strip()]
    for stmt in statements:
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            connection.commit()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                pass
            else:
                print(f"  Warning: {err}")


def load_table(connection, cursor, table_name):
    csv_path = os.path.join(DATA_DIR, f"{table_name}.csv")
    if not os.path.exists(csv_path):
        print(f"  Skipping {table_name}: CSV not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)

    cursor.execute(f"DELETE FROM {table_name}")
    connection.commit()

    cols = ", ".join(df.columns.tolist())
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

    batch_size = 500
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        cursor.executemany(insert_sql, batch)
        connection.commit()

    count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}") or cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  {table_name:15s}: {count:>6,} rows loaded")


def run_data_quality_checks(cursor):
    checks = {
        "Orphan refunds (no matching transaction)": """
            SELECT COUNT(*) FROM refunds r
            LEFT JOIN transactions t ON t.transaction_id = r.transaction_id
            WHERE t.transaction_id IS NULL
        """,
        "Orphan chargebacks (no matching transaction)": """
            SELECT COUNT(*) FROM chargebacks c
            LEFT JOIN transactions t ON t.transaction_id = c.transaction_id
            WHERE t.transaction_id IS NULL
        """,
        "Transactions with NULL amount": "SELECT COUNT(*) FROM transactions WHERE amount IS NULL",
        "Transactions with NULL status": "SELECT COUNT(*) FROM transactions WHERE status IS NULL",
        "Transactions with non-positive amount": "SELECT COUNT(*) FROM transactions WHERE amount <= 0",
        "Chargeback records with NULL reason_code": "SELECT COUNT(*) FROM chargebacks WHERE reason_code IS NULL",
    }

    print("\n  Data Quality Check Results:")
    all_pass = True
    for label, sql in checks.items():
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        status = "PASS" if count == 0 else f"FAIL ({count} issues)"
        if count > 0:
            all_pass = False
        print(f"    [{status:>12}]  {label}")

    if all_pass:
        print("\n  All data quality checks passed.")
    else:
        print("\n  Some checks failed — review data before proceeding.")


def main():
    print("Connecting to MySQL (no database)...")
    try:
        conn_plain = get_connection_no_db()
        cursor_plain = conn_plain.cursor()
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        print("Ensure MySQL is running and DB_USER / DB_PASSWORD env vars are set.")
        sys.exit(1)

    print("Creating database...")
    create_database(cursor_plain)
    cursor_plain.close()
    conn_plain.close()

    print("\nApplying schema...")
    conn = get_connection()
    cursor = conn.cursor()
    run_schema(conn, cursor)
    print("  Schema applied.")

    print("\nLoading data (ordered to respect foreign keys)...")
    for table in TABLE_ORDER:
        load_table(conn, cursor, table)

    run_data_quality_checks(cursor)

    cursor.close()
    conn.close()
    print("\nMySQL load complete.")


if __name__ == "__main__":
    main()
