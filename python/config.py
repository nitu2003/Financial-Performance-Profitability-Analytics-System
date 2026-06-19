from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
SQL_DIR = PROJECT_ROOT / "sql"
DDL_DIR = SQL_DIR / "ddl"
SQL_TESTS_DIR = SQL_DIR / "tests"

# Source CSV filenames (must exist under sources/)
SOURCE_FILES = {
    "customers": "customers.csv",
    "products": "products.csv",
    "regions": "regions.csv",
    "orders": "orders.csv",
    "order_lines": "order_lines.csv",
}

DDL_SCRIPT = DDL_DIR / "01_create_tables.sql"

# ---------------------------------------------------------------------------
# MySQL connection (loaded from .env)
# ---------------------------------------------------------------------------
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "financial_analytics")

# Bulk insert batch size for pandas → MySQL loads
LOAD_BATCH_SIZE = int(os.getenv("LOAD_BATCH_SIZE", "5000"))

# Tolerance for floating-point profit validation (currency)
PROFIT_TOLERANCE = float(os.getenv("PROFIT_TOLERANCE", "0.02"))


def mysql_connect_kwargs() -> dict:
    """Return keyword arguments for mysql.connector.connect."""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DATABASE,
        "autocommit": False,
    }


def source_path(name: str) -> Path:
    """Resolve a source CSV path by logical name (key in SOURCE_FILES)."""
    if name not in SOURCE_FILES:
        raise KeyError(f"Unknown source: {name}. Valid: {list(SOURCE_FILES)}")
    return SOURCES_DIR / SOURCE_FILES[name]
