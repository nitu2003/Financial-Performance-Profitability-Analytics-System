"""
Load source CSVs into MySQL staging tables, build dimensions and fact_sales.

Usage (from project root):
  python python/load_to_mysql.py

Requires MySQL running and credentials set via environment variables (see config.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import mysql.connector
import pandas as pd
from mysql.connector import MySQLConnection

# Allow running as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# ---------------------------------------------------------------------------
# Staging load definitions: CSV column → MySQL column
# ---------------------------------------------------------------------------
STAGING_SPECS: dict[str, dict[str, Any]] = {
    "stg_regions": {
        "file_key": "regions",
        "columns": ["region_id", "region_name", "country"],
        "dtypes": {"region_id": str, "region_name": str, "country": str},
    },
    "stg_products": {
        "file_key": "products",
        "columns": ["product_id", "product_name", "category", "unit_cost", "unit_price"],
        "dtypes": {
            "product_id": str,
            "product_name": str,
            "category": str,
            "unit_cost": float,
            "unit_price": float,
        },
    },
    "stg_customers": {
        "file_key": "customers",
        "columns": ["customer_id", "customer_name", "segment", "join_date"],
        "dtypes": {
            "customer_id": str,
            "customer_name": str,
            "segment": str,
            "join_date": str,
        },
        "date_columns": ["join_date"],
    },
    "stg_orders": {
        "file_key": "orders",
        "columns": ["order_id", "customer_id", "order_date", "region_id"],
        "dtypes": {
            "order_id": str,
            "customer_id": str,
            "order_date": str,
            "region_id": str,
        },
        "date_columns": ["order_date"],
    },
    "stg_order_lines": {
        "file_key": "order_lines",
        "columns": [
            "order_line_id",
            "order_id",
            "product_id",
            "quantity",
            "unit_price",
            "discount_percent",
            "unit_cost",
        ],
        "dtypes": {
            "order_line_id": str,
            "order_id": str,
            "product_id": str,
            "quantity": int,
            "unit_price": float,
            "discount_percent": float,
            "unit_cost": float,
        },
    },
}

TABLES_TRUNCATE_ORDER = [
    "fact_sales",
    "dim_date",
    "dim_customer",
    "dim_product",
    "dim_region",
    "stg_order_lines",
    "stg_orders",
    "stg_customers",
    "stg_products",
    "stg_regions",
]


def get_connection(use_database: bool = True) -> MySQLConnection:
    """Open a MySQL connection; optionally omit database for initial DDL."""
    kwargs = config.mysql_connect_kwargs()
    if not use_database:
        kwargs = {k: v for k, v in kwargs.items() if k != "database"}
    return mysql.connector.connect(**kwargs)


def execute_sql_file(conn: MySQLConnection, path: Path) -> None:
    """Execute a SQL script statement-by-statement (skips USE if already connected)."""
    sql_text = path.read_text(encoding="utf-8")
    # Remove single-line comments
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    cursor = conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    conn.commit()


def read_source_csv(file_key: str, spec: dict[str, Any]) -> pd.DataFrame:
    """Read and clean a source CSV for staging load."""
    path = config.source_path(file_key)
    df = pd.read_csv(path, dtype=spec.get("dtypes"), usecols=spec["columns"])

    for col in spec.get("date_columns", []):
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        if df[col].isna().any():
            bad = df[col].isna().sum()
            raise ValueError(f"{path.name}: {bad} invalid dates in column '{col}'")

    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(2)

    if "quantity" in df.columns:
        df["quantity"] = df["quantity"].astype(int)

    if "discount_percent" in df.columns:
        df["discount_percent"] = df["discount_percent"].fillna(0).round(2)

    # Drop rows with nulls in required fields
    before = len(df)
    df = df.dropna()
    if len(df) < before:
        print(f"  Warning: dropped {before - len(df)} rows with nulls from {path.name}")

    return df


def truncate_tables(conn: MySQLConnection) -> None:
    """Clear warehouse tables before reload (FK-safe order)."""
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in TABLES_TRUNCATE_ORDER:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cursor.close()
    conn.commit()


def bulk_insert(
    conn: MySQLConnection,
    table: str,
    df: pd.DataFrame,
    columns: list[str],
) -> int:
    """Insert a DataFrame into MySQL using executemany batches."""
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    rows = [tuple(row) for row in df[columns].itertuples(index=False, name=None)]
    cursor = conn.cursor()
    batch = config.LOAD_BATCH_SIZE
    for i in range(0, len(rows), batch):
        cursor.executemany(sql, rows[i : i + batch])
    cursor.close()
    conn.commit()
    return len(rows)


def load_staging(conn: MySQLConnection) -> None:
    """Load all staging tables from sources/."""
    print("\n--- Staging load ---")
    for table, spec in STAGING_SPECS.items():
        df = read_source_csv(spec["file_key"], spec)
        count = bulk_insert(conn, table, df, spec["columns"])
        print(f"  {table}: {count:,} rows")


def build_dimensions(conn: MySQLConnection) -> None:
    """Populate dimension tables from staging."""
    print("\n--- Dimension build ---")
    cursor = conn.cursor()

    dim_sql = [
        (
            "dim_region",
            """
            INSERT INTO dim_region (region_id, region_name, country)
            SELECT region_id, region_name, country FROM stg_regions
            """,
        ),
        (
            "dim_product",
            """
            INSERT INTO dim_product (product_id, product_name, category, unit_cost, unit_price)
            SELECT product_id, product_name, category, unit_cost, unit_price FROM stg_products
            """,
        ),
        (
            "dim_customer",
            """
            INSERT INTO dim_customer (customer_id, customer_name, segment, join_date)
            SELECT customer_id, customer_name, segment, join_date FROM stg_customers
            """,
        ),
        (
            "dim_date",
            """
            INSERT INTO dim_date (
                date_key, full_date, year, quarter, month, month_name,
                day_of_month, day_of_week, day_name, is_weekend
            )
            SELECT DISTINCT
                CAST(DATE_FORMAT(o.order_date, '%Y%m%d') AS UNSIGNED) AS date_key,
                o.order_date AS full_date,
                YEAR(o.order_date) AS year,
                QUARTER(o.order_date) AS quarter,
                MONTH(o.order_date) AS month,
                MONTHNAME(o.order_date) AS month_name,
                DAY(o.order_date) AS day_of_month,
                DAYOFWEEK(o.order_date) AS day_of_week,
                DAYNAME(o.order_date) AS day_name,
                CASE WHEN DAYOFWEEK(o.order_date) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend
            FROM stg_orders o
            ORDER BY full_date
            """,
        ),
    ]

    for table, sql in dim_sql:
        cursor.execute(sql)
        conn.commit()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} rows")

    cursor.close()


def build_fact_sales(conn: MySQLConnection) -> None:
    """Build fact_sales at order-line grain with revenue and profit metrics."""
    print("\n--- Fact build ---")
    sql = """
        INSERT INTO fact_sales (
            order_line_id, order_id, date_key, customer_key, product_key, region_key,
            quantity, unit_price, unit_cost, discount_percent,
            gross_revenue, discount_amount, net_revenue, cogs, gross_profit
        )
        SELECT
            ol.order_line_id,
            ol.order_id,
            CAST(DATE_FORMAT(o.order_date, '%Y%m%d') AS UNSIGNED) AS date_key,
            dc.customer_key,
            dp.product_key,
            dr.region_key,
            ol.quantity,
            ol.unit_price,
            ol.unit_cost,
            ol.discount_percent,
            ROUND(ol.quantity * ol.unit_price, 2) AS gross_revenue,
            ROUND((ol.quantity * ol.unit_price) * (ol.discount_percent / 100), 2) AS discount_amount,
            ROUND((ol.quantity * ol.unit_price) * (1 - ol.discount_percent / 100), 2) AS net_revenue,
            ROUND(ol.quantity * ol.unit_cost, 2) AS cogs,
            ROUND(
                (ol.quantity * ol.unit_price) * (1 - ol.discount_percent / 100)
                - (ol.quantity * ol.unit_cost),
                2
            ) AS gross_profit
        FROM stg_order_lines ol
        INNER JOIN stg_orders o ON ol.order_id = o.order_id
        INNER JOIN dim_customer dc ON o.customer_id = dc.customer_id
        INNER JOIN dim_product dp ON ol.product_id = dp.product_id
        INNER JOIN dim_region dr ON o.region_id = dr.region_id
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM fact_sales")
    count = cursor.fetchone()[0]
    cursor.close()
    print(f"  fact_sales: {count:,} rows")


def print_row_counts(conn: MySQLConnection) -> None:
    """Print final row counts for all warehouse tables."""
    tables = [
        "stg_regions",
        "stg_products",
        "stg_customers",
        "stg_orders",
        "stg_order_lines",
        "dim_region",
        "dim_product",
        "dim_customer",
        "dim_date",
        "fact_sales",
    ]
    print("\n--- Final row counts ---")
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:20} {count:>10,}")
    cursor.close()


def main() -> int:
    print("Financial Performance Analytics — MySQL load")
    print(f"  Database: {config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}")

    if not config.DDL_SCRIPT.exists():
        print(f"ERROR: DDL not found: {config.DDL_SCRIPT}")
        return 1

    for key in config.SOURCE_FILES:
        path = config.source_path(key)
        if not path.exists():
            print(f"ERROR: Missing source file: {path}")
            return 1

    try:
        # DDL creates database and tables (connect without default DB first)
        conn_admin = get_connection(use_database=False)
        print(f"\nExecuting DDL: {config.DDL_SCRIPT.name}")
        execute_sql_file(conn_admin, config.DDL_SCRIPT)
        conn_admin.close()

        conn = get_connection(use_database=True)
        truncate_tables(conn)
        load_staging(conn)
        build_dimensions(conn)
        build_fact_sales(conn)
        print_row_counts(conn)
        conn.close()

    except mysql.connector.Error as err:
        print(f"\nMySQL error: {err}")
        return 1

    print("\nLoad completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
