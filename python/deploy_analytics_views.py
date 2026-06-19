"""
Deploy analytics-layer SQL views (metrics + marts) to MySQL.

Usage:
  python python/deploy_analytics_views.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Run in dependency order
SQL_FILES = [
    config.SQL_DIR / "metrics" / "metric_revenue.sql",
    config.SQL_DIR / "metrics" / "metric_profit_margin.sql",
    config.SQL_DIR / "metrics" / "metric_aov.sql",
    config.SQL_DIR / "metrics" / "metric_mom_growth.sql",
    config.SQL_DIR / "metrics" / "metric_yoy_growth.sql",
    config.SQL_DIR / "marts" / "mart_product_profitability.sql",
    config.SQL_DIR / "marts" / "mart_region_profitability.sql",
    config.SQL_DIR / "marts" / "mart_customer_profitability.sql",
    config.SQL_DIR / "marts" / "mart_discount_impact.sql",
    config.SQL_DIR / "marts" / "mart_monthly_trends.sql",
    config.SQL_DIR / "marts" / "mart_loss_making_products.sql",
]


def execute_file(conn, path: Path) -> None:
    sql_text = path.read_text(encoding="utf-8")
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    cursor = conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    conn.commit()


def main() -> int:
    print("Deploying analytics views...")
    try:
        conn = mysql.connector.connect(**config.mysql_connect_kwargs())
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        return 1

    for path in SQL_FILES:
        if not path.exists():
            print(f"  MISSING: {path}")
            return 1
        print(f"  {path.relative_to(config.PROJECT_ROOT)}")
        execute_file(conn, path)

    conn.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
