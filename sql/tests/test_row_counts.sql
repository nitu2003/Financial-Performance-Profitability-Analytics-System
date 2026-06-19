-- =============================================================================
-- Row counts and referential integrity checks
-- Run after python/load_to_mysql.py (MySQL client or validation script)
-- =============================================================================

USE financial_analytics;

-- ---------------------------------------------------------------------------
-- 1. Staging table row counts
-- ---------------------------------------------------------------------------
SELECT 'stg_regions' AS table_name, COUNT(*) AS row_count FROM stg_regions
UNION ALL
SELECT 'stg_products', COUNT(*) FROM stg_products
UNION ALL
SELECT 'stg_customers', COUNT(*) FROM stg_customers
UNION ALL
SELECT 'stg_orders', COUNT(*) FROM stg_orders
UNION ALL
SELECT 'stg_order_lines', COUNT(*) FROM stg_order_lines;

-- ---------------------------------------------------------------------------
-- 2. Dimension table row counts
-- ---------------------------------------------------------------------------
SELECT 'dim_region' AS table_name, COUNT(*) AS row_count FROM dim_region
UNION ALL
SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date;

-- ---------------------------------------------------------------------------
-- 3. Fact table row count
-- ---------------------------------------------------------------------------
SELECT 'fact_sales' AS table_name, COUNT(*) AS row_count FROM fact_sales;

-- ---------------------------------------------------------------------------
-- 4. Staging vs dimension alignment (should be zero mismatches)
-- ---------------------------------------------------------------------------
SELECT 'orphan_stg_customers' AS check_name, COUNT(*) AS issue_count
FROM stg_customers sc
LEFT JOIN dim_customer dc ON sc.customer_id = dc.customer_id
WHERE dc.customer_key IS NULL

UNION ALL

SELECT 'orphan_stg_products', COUNT(*)
FROM stg_products sp
LEFT JOIN dim_product dp ON sp.product_id = dp.product_id
WHERE dp.product_key IS NULL

UNION ALL

SELECT 'orphan_stg_regions', COUNT(*)
FROM stg_regions sr
LEFT JOIN dim_region dr ON sr.region_id = dr.region_id
WHERE dr.region_key IS NULL;

-- ---------------------------------------------------------------------------
-- 5. Referential integrity: fact_sales → dimensions
-- ---------------------------------------------------------------------------
SELECT 'fact_missing_date' AS check_name, COUNT(*) AS issue_count
FROM fact_sales f
LEFT JOIN dim_date d ON f.date_key = d.date_key
WHERE d.date_key IS NULL

UNION ALL

SELECT 'fact_missing_customer', COUNT(*)
FROM fact_sales f
LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE c.customer_key IS NULL

UNION ALL

SELECT 'fact_missing_product', COUNT(*)
FROM fact_sales f
LEFT JOIN dim_product p ON f.product_key = p.product_key
WHERE p.product_key IS NULL

UNION ALL

SELECT 'fact_missing_region', COUNT(*)
FROM fact_sales f
LEFT JOIN dim_region r ON f.region_key = r.region_key
WHERE r.region_key IS NULL;

-- ---------------------------------------------------------------------------
-- 6. Fact grain vs staging order lines (should match)
-- ---------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM stg_order_lines) AS stg_line_count,
    (SELECT COUNT(*) FROM fact_sales) AS fact_line_count,
    (SELECT COUNT(*) FROM stg_order_lines) - (SELECT COUNT(*) FROM fact_sales) AS difference;

-- ---------------------------------------------------------------------------
-- 7. Orders without any fact lines (informational)
-- ---------------------------------------------------------------------------
SELECT COUNT(*) AS orders_without_lines
FROM stg_orders o
LEFT JOIN stg_order_lines ol ON o.order_id = ol.order_id
WHERE ol.order_line_id IS NULL;
