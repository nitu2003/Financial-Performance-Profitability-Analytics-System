"""
Data quality validation for the MySQL analytics warehouse.

Checks source files, staging/dimension/fact row counts, referential integrity,
duplicate keys, null keys, and gross_profit calculation accuracy.

Usage:
  python python/validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import mysql.connector
from mysql.connector import MySQLConnection

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Tables that must have at least one row after a successful load
WAREHOUSE_TABLES = [
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

KEY_COLUMNS = {
    "stg_customers": ["customer_id"],
    "stg_products": ["product_id"],
    "stg_regions": ["region_id"],
    "stg_orders": ["order_id", "customer_id", "order_date", "region_id"],
    "stg_order_lines": ["order_line_id", "order_id", "product_id"],
    "fact_sales": [
        "order_line_id",
        "order_id",
        "date_key",
        "customer_key",
        "product_key",
        "region_key",
    ],
}


class ValidationResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, message: str) -> None:
        self.passed.append(message)

    def fail(self, message: str) -> None:
        self.failed.append(message)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


def check_source_files(result: ValidationResult) -> None:
    """Verify all required CSV files exist under sources/."""
    print("\n--- Source files ---")
    for key, filename in config.SOURCE_FILES.items():
        path = config.SOURCES_DIR / filename
        if path.exists() and path.stat().st_size > 0:
            result.ok(f"Found {filename}")
            print(f"  OK  {filename}")
        else:
            result.fail(f"Missing or empty: {path}")
            print(f"  FAIL  {filename}")


def fetch_scalar(conn: MySQLConnection, sql: str) -> int:
    cursor = conn.cursor()
    cursor.execute(sql)
    value = cursor.fetchone()[0]
    cursor.close()
    return int(value)


def check_row_counts(conn: MySQLConnection, result: ValidationResult) -> None:
    """Ensure warehouse tables are populated."""
    print("\n--- Row counts ---")
    for table in WAREHOUSE_TABLES:
        try:
            count = fetch_scalar(conn, f"SELECT COUNT(*) FROM {table}")
        except mysql.connector.Error as err:
            result.fail(f"{table}: query failed — {err}")
            print(f"  FAIL  {table}: {err}")
            continue

        if count > 0:
            result.ok(f"{table}: {count:,} rows")
            print(f"  OK  {table}: {count:,}")
        else:
            result.fail(f"{table}: zero rows")
            print(f"  FAIL  {table}: 0 rows")


def check_duplicate_order_lines(conn: MySQLConnection, result: ValidationResult) -> None:
    """No duplicate order_line_id in staging or fact."""
    print("\n--- Duplicate order_line_id ---")
    for table, col in [("stg_order_lines", "order_line_id"), ("fact_sales", "order_line_id")]:
        dupes = fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM (
                SELECT {col} FROM {table}
                GROUP BY {col} HAVING COUNT(*) > 1
            ) t
            """,
        )
        if dupes == 0:
            result.ok(f"No duplicates in {table}.{col}")
            print(f"  OK  {table}")
        else:
            result.fail(f"{dupes} duplicate {col} in {table}")
            print(f"  FAIL  {table}: {dupes} duplicates")


def check_null_keys(conn: MySQLConnection, result: ValidationResult) -> None:
    """Key columns must not contain NULL."""
    print("\n--- Null key columns ---")
    for table, columns in KEY_COLUMNS.items():
        for col in columns:
            nulls = fetch_scalar(
                conn,
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL",
            )
            if nulls == 0:
                result.ok(f"{table}.{col}: no nulls")
            else:
                result.fail(f"{table}.{col}: {nulls} nulls")
                print(f"  FAIL  {table}.{col}: {nulls} nulls")
        if all(
            fetch_scalar(conn, f"SELECT COUNT(*) FROM {table} WHERE {c} IS NULL") == 0
            for c in columns
        ):
            print(f"  OK  {table}")


def check_foreign_keys(conn: MySQLConnection, result: ValidationResult) -> None:
    """Validate staging and fact referential relationships."""
    print("\n--- Foreign key relationships ---")
    checks = [
        (
            "stg_orders -> stg_customers",
            """
            SELECT COUNT(*) FROM stg_orders o
            LEFT JOIN stg_customers c ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
            """,
        ),
        (
            "stg_orders -> stg_regions",
            """
            SELECT COUNT(*) FROM stg_orders o
            LEFT JOIN stg_regions r ON o.region_id = r.region_id
            WHERE r.region_id IS NULL
            """,
        ),
        (
            "stg_order_lines -> stg_orders",
            """
            SELECT COUNT(*) FROM stg_order_lines ol
            LEFT JOIN stg_orders o ON ol.order_id = o.order_id
            WHERE o.order_id IS NULL
            """,
        ),
        (
            "stg_order_lines -> stg_products",
            """
            SELECT COUNT(*) FROM stg_order_lines ol
            LEFT JOIN stg_products p ON ol.product_id = p.product_id
            WHERE p.product_id IS NULL
            """,
        ),
        (
            "fact_sales -> dim_date",
            """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_date d ON f.date_key = d.date_key
            WHERE d.date_key IS NULL
            """,
        ),
        (
            "fact_sales -> dim_customer",
            """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
            WHERE c.customer_key IS NULL
            """,
        ),
        (
            "fact_sales -> dim_product",
            """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_product p ON f.product_key = p.product_key
            WHERE p.product_key IS NULL
            """,
        ),
        (
            "fact_sales -> dim_region",
            """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_region r ON f.region_key = r.region_key
            WHERE r.region_key IS NULL
            """,
        ),
    ]

    for label, sql in checks:
        orphans = fetch_scalar(conn, sql)
        if orphans == 0:
            result.ok(label)
            print(f"  OK  {label}")
        else:
            result.fail(f"{label}: {orphans} orphan rows")
            print(f"  FAIL  {label}: {orphans} orphans")


def check_profit_calculations(conn: MySQLConnection, result: ValidationResult) -> None:
    """Verify revenue and profit formulas on fact_sales."""
    print("\n--- Profit calculations ---")
    tol = config.PROFIT_TOLERANCE

    checks = [
        (
            "gross_revenue = quantity * unit_price",
            f"""
            SELECT COUNT(*) FROM fact_sales
            WHERE ABS(gross_revenue - (quantity * unit_price)) > {tol}
            """,
        ),
        (
            "discount_amount = gross_revenue * discount_percent / 100",
            f"""
            SELECT COUNT(*) FROM fact_sales
            WHERE ABS(discount_amount - (gross_revenue * discount_percent / 100)) > {tol}
            """,
        ),
        (
            "net_revenue = gross_revenue - discount_amount",
            f"""
            SELECT COUNT(*) FROM fact_sales
            WHERE ABS(net_revenue - (gross_revenue - discount_amount)) > {tol}
            """,
        ),
        (
            "cogs = quantity * unit_cost",
            f"""
            SELECT COUNT(*) FROM fact_sales
            WHERE ABS(cogs - (quantity * unit_cost)) > {tol}
            """,
        ),
        (
            "gross_profit = net_revenue - cogs",
            f"""
            SELECT COUNT(*) FROM fact_sales
            WHERE ABS(gross_profit - (net_revenue - cogs)) > {tol}
            """,
        ),
    ]

    for label, sql in checks:
        bad = fetch_scalar(conn, sql)
        if bad == 0:
            result.ok(label)
            print(f"  OK  {label}")
        else:
            result.fail(f"{label}: {bad} mismatched rows")
            print(f"  FAIL  {label}: {bad} rows")


def check_fact_vs_staging_count(conn: MySQLConnection, result: ValidationResult) -> None:
    """fact_sales row count should match stg_order_lines."""
    print("\n--- Fact vs staging line count ---")
    stg = fetch_scalar(conn, "SELECT COUNT(*) FROM stg_order_lines")
    fact = fetch_scalar(conn, "SELECT COUNT(*) FROM fact_sales")
    if stg == fact:
        result.ok(f"fact_sales matches stg_order_lines ({fact:,})")
        print(f"  OK  {fact:,} lines in both")
    else:
        result.fail(f"Count mismatch: stg={stg:,}, fact={fact:,}")
        print(f"  FAIL  stg={stg:,}, fact={fact:,}")


def main() -> int:
    print("Financial Performance Analytics — Validation")
    result = ValidationResult()

    check_source_files(result)

    try:
        conn = mysql.connector.connect(**config.mysql_connect_kwargs())
    except mysql.connector.Error as err:
        print(f"\nCannot connect to MySQL: {err}")
        print("Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE and retry.")
        return 1

    try:
        check_row_counts(conn, result)
        check_duplicate_order_lines(conn, result)
        check_null_keys(conn, result)
        check_foreign_keys(conn, result)
        check_profit_calculations(conn, result)
        check_fact_vs_staging_count(conn, result)
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print(f"Passed: {len(result.passed)}  |  Failed: {len(result.failed)}")
    if result.failed:
        print("\nFailures:")
        for msg in result.failed:
            print(f"  - {msg}")
        return 1

    print("\nAll validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
