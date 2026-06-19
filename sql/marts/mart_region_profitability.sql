-- =============================================================================
-- mart_region_profitability.sql
-- Regional performance with monthly trends for geo dashboards.
-- Grain: region_key + year + month
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW mart_region_profitability AS
SELECT
    r.region_key,
    r.region_id,
    r.region_name,
    r.country,
    d.year,
    d.month,
    MIN(d.month_name)                                                   AS month_name,
    STR_TO_DATE(CONCAT(d.year, '-', LPAD(d.month, 2, '0'), '-01'), '%Y-%m-%d')
                                                                        AS month_start_date,
    CAST(CONCAT(d.year, LPAD(d.month, 2, '0')) AS UNSIGNED)             AS year_month_key,
    SUM(f.net_revenue)                                                  AS net_revenue,
    SUM(f.gross_revenue)                                                AS gross_revenue,
    SUM(f.gross_profit)                                                 AS gross_profit,
    SUM(f.discount_amount)                                              AS total_discount_amount,
    SUM(f.quantity)                                                     AS units_sold,
    COUNT(DISTINCT f.order_id)                                          AS order_count,
    COUNT(DISTINCT f.customer_key)                                      AS customer_count,
    COUNT(DISTINCT f.product_key)                                       AS products_sold_count,
    ROUND(100.0 * SUM(f.gross_profit) / NULLIF(SUM(f.net_revenue), 0), 2)
                                                                        AS profit_margin_pct,
    ROUND(SUM(f.net_revenue) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2)
                                                                        AS average_order_value,
    ROUND(AVG(f.discount_percent), 2)                                   AS avg_discount_pct,
    -- Share of company revenue in the month
    ROUND(
        100.0 * SUM(f.net_revenue) / NULLIF(SUM(SUM(f.net_revenue)) OVER (
            PARTITION BY d.year, d.month
        ), 0),
        2
    )                                                                   AS revenue_share_pct
FROM fact_sales AS f
INNER JOIN dim_region AS r ON f.region_key = r.region_key
INNER JOIN dim_date AS d ON f.date_key = d.date_key
GROUP BY
    r.region_key, r.region_id, r.region_name, r.country,
    d.year, d.month;
