"""
Generate realistic synthetic retail/ecommerce source data for the
Financial Performance & Profitability Analytics System.

Outputs CSV files to sources/:
  customers.csv, products.csv, regions.csv, orders.csv, order_lines.csv
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths & reproducibility
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Simulation window: 2+ years of daily orders
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Target scale
TARGET_ORDER_LINES = 100_000
N_CUSTOMERS = 8_000
N_PRODUCTS = 280

SEGMENTS = ["Consumer", "Corporate", "Small Business"]
CATEGORIES = ["Electronics", "Furniture", "Office Supplies", "Accessories", "Appliances"]

# Discount campaign months (month number): deeper discounts in these periods
CAMPAIGN_MONTHS = {
    1: 0.15,   # January clearance
    6: 0.12,   # Mid-year sale
    7: 0.10,   # Summer promotions
    11: 0.20,  # Black Friday build-up
    12: 0.18,  # Holiday / festive season
}

# Festive / holiday demand multipliers by month (revenue seasonality)
MONTH_DEMAND_MULTIPLIER = {
    1: 0.85,
    2: 0.90,
    3: 0.95,
    4: 0.98,
    5: 1.00,
    6: 1.05,
    7: 1.02,
    8: 1.00,
    9: 1.05,
    10: 1.10,
    11: 1.45,  # Pre-holiday surge
    12: 1.55,  # Peak festive season
}

# Category seasonality tweaks (multiplier by month index 1-12)
CATEGORY_SEASONALITY = {
    "Electronics": [0.9, 0.85, 0.9, 0.95, 1.0, 1.0, 0.95, 1.0, 1.05, 1.1, 1.35, 1.5],
    "Furniture": [0.85, 0.9, 1.0, 1.05, 1.1, 1.0, 0.95, 0.9, 1.0, 1.05, 1.2, 1.15],
    "Office Supplies": [0.95, 1.0, 1.1, 1.05, 1.0, 0.95, 0.9, 1.15, 1.2, 1.0, 0.95, 0.9],
    "Accessories": [0.9, 0.95, 1.0, 1.0, 1.05, 1.1, 1.05, 1.0, 1.0, 1.1, 1.3, 1.4],
    "Appliances": [0.9, 0.9, 1.0, 1.05, 1.1, 1.05, 1.0, 0.95, 1.0, 1.05, 1.25, 1.35],
}

# Regional performance: order volume weight + margin pressure (discount tendency)
REGIONS_SPEC = [
    ("REG-001", "Northeast", "United States", 1.15, 1.02),
    ("REG-002", "Pacific", "United States", 1.20, 1.00),
    ("REG-003", "Southeast", "United States", 1.05, 0.98),
    ("REG-004", "Midwest", "United States", 0.95, 0.97),
    ("REG-005", "United Kingdom", "United Kingdom", 1.10, 1.01),
    ("REG-006", "DACH", "Germany", 1.08, 0.99),
    ("REG-007", "Nordics", "Sweden", 0.90, 1.03),
    ("REG-008", "ANZ", "Australia", 0.88, 1.00),
    ("REG-009", "India Metro", "India", 1.25, 0.92),
    ("REG-010", "UAE Hub", "United Arab Emirates", 0.85, 1.05),
]

FIRST_NAMES = [
    "James", "Maria", "Robert", "Priya", "Michael", "Sarah", "David", "Emma",
    "Chen", "Aisha", "Daniel", "Sofia", "William", "Olivia", "Raj", "Fatima",
    "Thomas", "Hannah", "Carlos", "Yuki", "Ahmed", "Lisa", "Kevin", "Nina",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Lee", "Wilson", "Anderson", "Taylor",
    "Thomas", "Moore", "Jackson", "Martin", "Thompson", "White", "Harris",
    "Clark", "Lewis", "Walker", "Hall", "Allen", "Young", "King", "Wright",
]
COMPANY_PREFIXES = [
    "Apex", "Summit", "Nova", "Vertex", "Pioneer", "Horizon", "Atlas", "Meridian",
    "Catalyst", "Fusion", "Nexus", "Prime", "Sterling", "Vantage", "Core",
]
COMPANY_SUFFIXES = [
    "Trading", "Solutions", "Group", "Industries", "Partners", "Supply Co",
    "Enterprises", "Systems", "Logistics", "Retail",
]

PRODUCT_ADJECTIVES = [
    "Pro", "Elite", "Essential", "Compact", "Premium", "Standard", "Ultra",
    "Classic", "Smart", "Eco", "Deluxe", "Lite", "Max", "Plus",
]
PRODUCT_NOUNS = {
    "Electronics": ["Laptop", "Monitor", "Tablet", "Headphones", "Camera", "Speaker", "Router", "Keyboard"],
    "Furniture": ["Desk", "Chair", "Cabinet", "Bookshelf", "Table", "Sofa", "Wardrobe", "Stool"],
    "Office Supplies": ["Notebook", "Pen Set", "Stapler", "Paper Ream", "Binder", "Markers", "Envelopes", "Planner"],
    "Accessories": ["Case", "Cable", "Stand", "Adapter", "Mount", "Sleeve", "Hub", "Charger"],
    "Appliances": ["Microwave", "Blender", "Vacuum", "Toaster", "Kettle", "Air Fryer", "Heater", "Fan"],
}

# Price bands by category (min, max) for base unit_price before margin profile
CATEGORY_PRICE_BANDS = {
    "Electronics": (29.99, 2499.99),
    "Furniture": (79.99, 2999.99),
    "Office Supplies": (4.99, 149.99),
    "Accessories": (9.99, 199.99),
    "Appliances": (149.99, 3499.99),
}


def _date_range(start: datetime, end: datetime) -> pd.DatetimeIndex:
    """Inclusive daily date range."""
    return pd.date_range(start=start.date(), end=end.date(), freq="D")


def generate_regions() -> pd.DataFrame:
    """Build region dimension with country and performance metadata."""
    regions = pd.DataFrame(
        REGIONS_SPEC,
        columns=[
            "region_id",
            "region_name",
            "country",
            "volume_weight",
            "margin_index",
        ],
    )
    return regions[["region_id", "region_name", "country"]], regions


def generate_products(n_products: int = N_PRODUCTS) -> pd.DataFrame:
    """
    Create product catalog with mixed margin profiles:
    - loss_making: price at or below cost; heavy discount exposure
    - low_margin: high velocity, thin margin
    - standard / premium: healthier margins
    """
    rows = []
    per_category = n_products // len(CATEGORIES)
    product_idx = 0

    # Distribution of margin archetypes across catalog
    profile_pool = (
        ["loss_making"] * int(n_products * 0.08)
        + ["low_margin"] * int(n_products * 0.22)
        + ["standard"] * int(n_products * 0.50)
        + ["premium"] * int(n_products * 0.20)
    )
    rng = np.random.default_rng(RANDOM_SEED)
    rng.shuffle(profile_pool)
    # Pad or trim to exact length
    while len(profile_pool) < n_products:
        profile_pool.append("standard")
    profile_pool = profile_pool[:n_products]

    for category in CATEGORIES:
        nouns = PRODUCT_NOUNS[category]
        low, high = CATEGORY_PRICE_BANDS[category]
        for i in range(per_category):
            profile = profile_pool[product_idx]
            adj = rng.choice(PRODUCT_ADJECTIVES)
            noun = nouns[i % len(nouns)]
            product_name = f"{adj} {noun} {category.split()[0][:3]}-{product_idx + 1:03d}"
            product_id = f"PRD-{product_idx + 1:05d}"

            # Base catalog price from category band (log-uniform feels realistic for retail)
            log_low, log_high = np.log(low), np.log(high)
            unit_price = float(np.exp(rng.uniform(log_low, log_high)))
            unit_price = round(unit_price, 2)

            if profile == "loss_making":
                # Sold near or below cost; promotions often push lines negative
                margin_pct = rng.uniform(-0.05, 0.04)
            elif profile == "low_margin":
                margin_pct = rng.uniform(0.03, 0.08)
            elif profile == "standard":
                margin_pct = rng.uniform(0.15, 0.35)
            else:  # premium
                margin_pct = rng.uniform(0.40, 0.60)

            unit_cost = round(unit_price * (1 - margin_pct), 2)
            unit_cost = max(0.01, unit_cost)

            rows.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "unit_cost": unit_cost,
                    "unit_price": unit_price,
                    "_margin_profile": profile,
                    "_demand_weight": _demand_weight_for_profile(profile, rng),
                }
            )
            product_idx += 1

    return pd.DataFrame(rows)


def _demand_weight_for_profile(profile: str, rng: np.random.Generator) -> float:
    """High-volume SKUs skew toward low-margin and electronics/accessories."""
    base = {
        "loss_making": rng.uniform(1.2, 2.5),   # clearance drivers, high units
        "low_margin": rng.uniform(1.5, 3.0),      # bestsellers, thin margin
        "standard": rng.uniform(0.6, 1.4),
        "premium": rng.uniform(0.2, 0.8),
    }
    return base[profile]


def generate_customers(n_customers: int = N_CUSTOMERS) -> pd.DataFrame:
    """
    Customer master with B2C and B2B naming patterns.
    join_date spread over 4 years before simulation end so repeat buyers exist.
    """
    rng = np.random.default_rng(RANDOM_SEED + 1)
    segment_probs = [0.62, 0.18, 0.20]  # Consumer, Corporate, Small Business
    segments = rng.choice(SEGMENTS, size=n_customers, p=segment_probs)

    join_start = START_DATE - timedelta(days=365 * 4)
    join_end = END_DATE - timedelta(days=30)
    join_days = (join_end - join_start).days
    join_offsets = rng.integers(0, join_days, size=n_customers)
    join_dates = [join_start + timedelta(days=int(d)) for d in join_offsets]

    names = []
    for i, seg in enumerate(segments):
        if seg == "Consumer":
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        else:
            prefix = rng.choice(COMPANY_PREFIXES)
            suffix = rng.choice(COMPANY_SUFFIXES)
            name = f"{prefix} {suffix}"
            if seg == "Small Business" and rng.random() < 0.35:
                name = f"{name} LLC"
        names.append(name)

    customers = pd.DataFrame(
        {
            "customer_id": [f"CUS-{i + 1:06d}" for i in range(n_customers)],
            "customer_name": names,
            "segment": segments,
            "join_date": [d.strftime("%Y-%m-%d") for d in join_dates],
        }
    )
    return customers


def _build_customer_weights(customers: pd.DataFrame) -> np.ndarray:
    """
    Pareto-style weights so ~25% of customers drive ~65% of orders (repeat buyers).
  Corporate/SMB get fewer but larger orders handled separately in quantity logic.
    """
    rng = np.random.default_rng(RANDOM_SEED + 2)
    n = len(customers)
    weights = rng.pareto(a=1.8, size=n) + 0.1
    # Corporate accounts order less frequently; quantity per line is boosted instead
    seg = customers["segment"].values
    weights[seg == "Corporate"] *= 0.35
    weights[seg == "Small Business"] *= 0.55
    return weights / weights.sum()


def _daily_order_counts(dates: pd.DatetimeIndex, regions_meta: pd.DataFrame) -> pd.DataFrame:
    """
    Allocate total orders across days and regions using seasonality and regional weights.
    Calibrated so expected line count exceeds TARGET_ORDER_LINES.
    """
    rng = np.random.default_rng(RANDOM_SEED + 3)
    n_days = len(dates)
    n_regions = len(regions_meta)

    # Average lines per order varies by period (holiday baskets are larger)
    avg_lines_base = 2.35
    total_days = n_days

    # Rough calibration: total_orders * avg_lines ≈ TARGET
    estimated_orders = int(TARGET_ORDER_LINES / avg_lines_base)

    region_vol = regions_meta["volume_weight"].values
    region_vol = region_vol / region_vol.sum()

    records = []
    for d in dates:
        month = d.month
        demand = MONTH_DEMAND_MULTIPLIER[month]
        # Weekend lift for B2C-heavy retail
        if d.dayofweek >= 5:
            demand *= 1.08
        base_orders = (estimated_orders / total_days) * demand
        # Poisson noise per day
        n_orders_day = max(0, rng.poisson(base_orders))
        if n_orders_day == 0:
            continue
        region_counts = rng.multinomial(n_orders_day, region_vol)
        for reg_idx, count in enumerate(region_counts):
            if count > 0:
                records.append(
                    {
                        "order_date": d,
                        "region_id": regions_meta.iloc[reg_idx]["region_id"],
                        "n_orders": count,
                    }
                )

    return pd.DataFrame(records)


def generate_orders_and_lines(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    regions_meta: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate orders and order lines with valid FK relationships,
    campaign discounts, and segment/region-specific behavior.
    """
    rng = np.random.default_rng(RANDOM_SEED + 4)
    dates = _date_range(START_DATE, END_DATE)
    customer_weights = _build_customer_weights(customers)
    customer_ids = customers["customer_id"].values
    customer_seg = customers.set_index("customer_id")["segment"]
    join_dates = pd.to_datetime(customers["join_date"])

    # Eligible customers per day (joined before order date)
    cust_join_map = dict(zip(customers["customer_id"], join_dates))

    products_work = products.copy()
    cat_season = CATEGORY_SEASONALITY

    # Product sampling weights by category and SKU demand
    prod_ids = products_work["product_id"].values
    prod_cat = products_work["category"].values
    prod_weights = products_work["_demand_weight"].values
    prod_price = products_work["unit_price"].values
    prod_cost = products_work["unit_cost"].values
    prod_profile = products_work["_margin_profile"].values

    prod_idx_by_id = {pid: i for i, pid in enumerate(prod_ids)}
    categories_arr = np.array(CATEGORIES)
    cat_to_indices = {c: np.where(prod_cat == c)[0] for c in CATEGORIES}

    region_margin = regions_meta.set_index("region_id")["margin_index"].to_dict()

    daily_plan = _daily_order_counts(dates, regions_meta)

    orders_rows = []
    lines_rows = []
    order_counter = 0
    line_counter = 0

    for _, day_row in daily_plan.iterrows():
        order_date = day_row["order_date"]
        region_id = day_row["region_id"]
        n_orders = int(day_row["n_orders"])
        month = order_date.month
        campaign_discount = CAMPAIGN_MONTHS.get(month, 0.0)
        demand_mult = MONTH_DEMAND_MULTIPLIER[month]
        margin_idx = region_margin[region_id]

        # Filter customers who had joined by this date
        eligible_mask = join_dates <= pd.Timestamp(order_date)
        if not eligible_mask.any():
            continue
        eligible_weights = customer_weights.copy()
        eligible_weights[~eligible_mask] = 0
        if eligible_weights.sum() <= 0:
            continue
        eligible_weights = eligible_weights / eligible_weights.sum()

        chosen_customers = rng.choice(
            customer_ids,
            size=n_orders,
            replace=True,
            p=eligible_weights,
        )

        for cust_id in chosen_customers:
            order_counter += 1
            order_id = f"ORD-{order_counter:08d}"
            seg = customer_seg[cust_id]

            orders_rows.append(
                {
                    "order_id": order_id,
                    "customer_id": cust_id,
                    "order_date": order_date.strftime("%Y-%m-%d"),
                    "region_id": region_id,
                }
            )

            # Lines per order: Corporate fewer lines but higher qty; holidays more lines
            if seg == "Corporate":
                n_lines = int(rng.integers(1, 5))
                qty_scale = rng.integers(5, 40)
            elif seg == "Small Business":
                n_lines = int(rng.integers(1, 6))
                qty_scale = rng.integers(2, 15)
            else:
                n_lines = int(rng.integers(1, 5))
                qty_scale = 1

            if month in (11, 12):
                n_lines = min(n_lines + int(rng.integers(0, 3)), 8)

            # Category mix influenced by month seasonality
            cat_weights = np.array(
                [cat_season[c][month - 1] for c in CATEGORIES],
                dtype=float,
            )
            cat_weights = cat_weights / cat_weights.sum()

            for _ in range(n_lines):
                line_counter += 1
                order_line_id = f"OLN-{line_counter:09d}"

                category = rng.choice(categories_arr, p=cat_weights)
                candidate_idx = cat_to_indices[category]
                sku_weights = prod_weights[candidate_idx]
                sku_weights = sku_weights / sku_weights.sum()
                p_idx = candidate_idx[rng.choice(len(candidate_idx), p=sku_weights)]
                product_id = prod_ids[p_idx]

                catalog_price = prod_price[p_idx]
                unit_cost = prod_cost[p_idx]
                profile = prod_profile[p_idx]

                # Small price variation (list price overrides, regional pricing)
                price_noise = rng.uniform(0.97, 1.03)
                unit_price = round(float(catalog_price) * price_noise, 2)

                # Quantity with realistic variation
                if seg == "Consumer":
                    quantity = int(rng.integers(1, 4))
                elif seg == "Small Business":
                    quantity = int(rng.integers(1, 8) * max(1, qty_scale // 3))
                else:
                    quantity = int(rng.integers(2, 12) * max(1, qty_scale // 5))
                quantity = max(1, quantity)

                # Discount logic: campaigns + loss-leaders + regional pressure
                base_discount = 0.0
                if campaign_discount > 0 and rng.random() < 0.55:
                    base_discount = campaign_discount * rng.uniform(0.5, 1.0)

                if profile in ("loss_making", "low_margin") and month in CAMPAIGN_MONTHS:
                    base_discount = max(base_discount, rng.uniform(0.10, 0.35))

                if profile == "loss_making":
                    base_discount = max(base_discount, rng.uniform(0.05, 0.25))

                # Regions with lower margin_index run sharper promos
                if margin_idx < 1.0:
                    base_discount += rng.uniform(0, 0.08)

                # Corporate negotiated discounts
                if seg == "Corporate":
                    base_discount = max(base_discount, rng.uniform(0.05, 0.20))

                discount_percent = round(min(base_discount * 100, 45.0), 2)

                lines_rows.append(
                    {
                        "order_line_id": order_line_id,
                        "order_id": order_id,
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "discount_percent": discount_percent,
                        "unit_cost": unit_cost,
                    }
                )

    orders = pd.DataFrame(orders_rows)
    order_lines = pd.DataFrame(lines_rows)
    return orders, order_lines


def _ensure_minimum_lines(order_lines: pd.DataFrame, orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Top up with additional lines if randomness undershoots the 100k target."""
    if len(order_lines) >= TARGET_ORDER_LINES:
        return order_lines

    rng = np.random.default_rng(RANDOM_SEED + 99)
    shortfall = TARGET_ORDER_LINES - len(order_lines)

    prod_ids = products["product_id"].values
    prod_price = products.set_index("product_id")["unit_price"]
    prod_cost = products.set_index("product_id")["unit_cost"]
    order_ids = orders["order_id"].values
    line_counter = int(order_lines["order_line_id"].str.split("-").str[1].astype(int).max())

    extra_rows = []
    for i in range(shortfall):
        line_counter += 1
        oid = rng.choice(order_ids)
        pid = rng.choice(prod_ids)
        extra_rows.append(
            {
                "order_line_id": f"OLN-{line_counter:09d}",
                "order_id": oid,
                "product_id": pid,
                "quantity": int(rng.integers(1, 5)),
                "unit_price": round(float(prod_price[pid]) * rng.uniform(0.98, 1.02), 2),
                "discount_percent": round(float(rng.uniform(0, 0.15) * 100), 2),
                "unit_cost": float(prod_cost[pid]),
            }
        )

    return pd.concat([order_lines, pd.DataFrame(extra_rows)], ignore_index=True)


def print_summary(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    regions: pd.DataFrame,
    orders: pd.DataFrame,
    order_lines: pd.DataFrame,
) -> None:
    """Print dataset sizes, revenue/profit metrics, and sample insights."""
    lines = order_lines.copy()
    lines["gross_revenue"] = lines["quantity"] * lines["unit_price"]
    lines["discount_amount"] = lines["gross_revenue"] * (lines["discount_percent"] / 100)
    lines["net_revenue"] = lines["gross_revenue"] - lines["discount_amount"]
    lines["cogs"] = lines["quantity"] * lines["unit_cost"]
    lines["gross_profit"] = lines["net_revenue"] - lines["cogs"]

    merged = lines.merge(products[["product_id", "category", "product_name"]], on="product_id")
    merged = merged.merge(
        orders[["order_id", "customer_id", "order_date", "region_id"]],
        on="order_id",
    )
    merged = merged.merge(regions, on="region_id", how="left")
    merged = merged.merge(customers[["customer_id", "segment"]], on="customer_id")
    merged["order_date"] = pd.to_datetime(merged["order_date"])
    merged["month"] = merged["order_date"].dt.to_period("M").astype(str)

    print("\n" + "=" * 72)
    print("DATASET SIZES")
    print("=" * 72)
    for name, df in [
        ("customers", customers),
        ("products", products),
        ("regions", regions),
        ("orders", orders),
        ("order_lines", order_lines),
    ]:
        print(f"  {name:14} {len(df):>10,} rows")

    date_min = merged["order_date"].min().date()
    date_max = merged["order_date"].max().date()
    print(f"\n  Date range: {date_min} to {date_max} ({(date_max - date_min).days + 1} days)")

    print("\n" + "=" * 72)
    print("SUMMARY STATISTICS")
    print("=" * 72)
    print(f"  Total gross revenue:  ${lines['gross_revenue'].sum():>18,.2f}")
    print(f"  Total net revenue:    ${lines['net_revenue'].sum():>18,.2f}")
    print(f"  Total COGS:           ${lines['cogs'].sum():>18,.2f}")
    print(f"  Total gross profit:   ${lines['gross_profit'].sum():>18,.2f}")
    margin = lines["gross_profit"].sum() / lines["net_revenue"].sum() * 100
    print(f"  Overall margin:       {margin:>18.2f}%")
    print(f"  Avg discount %:       {lines['discount_percent'].mean():>18.2f}%")
    print(f"  Avg lines per order:  {len(lines) / len(orders):>18.2f}")

    repeat_customers = orders.groupby("customer_id").size()
    repeat_rate = (repeat_customers > 1).mean() * 100
    print(f"  Repeat customer rate: {repeat_rate:>17.1f}%")

    print("\n" + "=" * 72)
    print("SAMPLE PROFITABILITY INSIGHTS")
    print("=" * 72)

    by_cat = merged.groupby("category").agg(
        net_revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    by_cat["margin_pct"] = by_cat["gross_profit"] / by_cat["net_revenue"] * 100
    print("\n  Profitability by category:")
    print(by_cat.sort_values("net_revenue", ascending=False).to_string(float_format=lambda x: f"{x:,.2f}"))

    by_region = merged.groupby("region_name").agg(
        net_revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    by_region["margin_pct"] = by_region["gross_profit"] / by_region["net_revenue"] * 100
    print("\n  Top 5 regions by net revenue:")
    print(by_region.sort_values("net_revenue", ascending=False).head().to_string(float_format=lambda x: f"{x:,.2f}"))

    by_month = merged.groupby("month").agg(net_revenue=("net_revenue", "sum")).sort_index()
    peak_month = by_month["net_revenue"].idxmax()
    low_month = by_month["net_revenue"].idxmin()
    print(f"\n  Peak revenue month:   {peak_month} (${by_month.loc[peak_month, 'net_revenue']:,.0f})")
    print(f"  Lowest revenue month: {low_month} (${by_month.loc[low_month, 'net_revenue']:,.0f})")

    by_product = merged.groupby(["product_id", "product_name"]).agg(
        gross_profit=("gross_profit", "sum"),
        net_revenue=("net_revenue", "sum"),
        units=("quantity", "sum"),
    )
    loss_products = by_product[by_product["gross_profit"] < 0].sort_values("gross_profit")
    print(f"\n  Loss-making products: {len(loss_products)} SKUs")
    if len(loss_products) > 0:
        print("  Worst 5 by profit:")
        print(loss_products.head().to_string(float_format=lambda x: f"{x:,.2f}"))

    high_vol = by_product.sort_values("units", ascending=False).head(5)
    high_vol = high_vol.merge(
        products.set_index("product_id")[["unit_price", "unit_cost"]],
        left_index=True,
        right_index=True,
    )
    high_vol["catalog_margin_pct"] = (
        (high_vol["unit_price"] - high_vol["unit_cost"]) / high_vol["unit_price"] * 100
    )
    print("\n  High-volume SKUs (catalog margin % shown):")
    print(
        high_vol[["units", "net_revenue", "gross_profit", "catalog_margin_pct"]]
        .to_string(float_format=lambda x: f"{x:,.2f}")
    )

    seg_summary = merged.groupby("segment").agg(
        orders=("order_id", "nunique"),
        net_revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    print("\n  Performance by customer segment:")
    print(seg_summary.to_string(float_format=lambda x: f"{x:,.0f}"))

    print("\n" + "=" * 72)


def main() -> int:
    """Orchestrate generation and write CSVs to sources/."""
    print("Generating synthetic retail financial data...")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Output dir:   {SOURCES_DIR}")
    print(f"  Random seed:  {RANDOM_SEED}")

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    regions, regions_meta = generate_regions()
    products_full = generate_products(N_PRODUCTS)
    products = products_full[
        ["product_id", "product_name", "category", "unit_cost", "unit_price"]
    ].copy()
    customers = generate_customers(N_CUSTOMERS)
    orders, order_lines = generate_orders_and_lines(customers, products_full, regions_meta)

    if len(order_lines) < TARGET_ORDER_LINES:
        order_lines = _ensure_minimum_lines(order_lines, orders, products)

    # Persist public columns only
    customers.to_csv(SOURCES_DIR / "customers.csv", index=False)
    products.to_csv(SOURCES_DIR / "products.csv", index=False)
    regions.to_csv(SOURCES_DIR / "regions.csv", index=False)
    orders.to_csv(SOURCES_DIR / "orders.csv", index=False)
    order_lines.to_csv(SOURCES_DIR / "order_lines.csv", index=False)

    print("\nFiles written:")
    for fname in ["customers.csv", "products.csv", "regions.csv", "orders.csv", "order_lines.csv"]:
        path = SOURCES_DIR / fname
        print(f"  {path}")

    print_summary(customers, products, regions, orders, order_lines)

    # Referential integrity checks
    assert orders["customer_id"].isin(customers["customer_id"]).all()
    assert orders["region_id"].isin(regions["region_id"]).all()
    assert order_lines["order_id"].isin(orders["order_id"]).all()
    assert order_lines["product_id"].isin(products["product_id"]).all()
    assert len(order_lines) >= TARGET_ORDER_LINES

    print("Referential integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
