-- =============================================================================
-- mart_discount_impact.sql
-- Discount band analysis: revenue foregone, margin impact, profitability.
-- Grain: year + month + discount_band (+ category for drill-down)
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW mart_discount_impact AS
WITH line_enriched AS (
    SELECT
        f.order_line_id,
        f.order_id,
        f.net_revenue,
        f.gross_revenue,
        f.gross_profit,
        f.discount_amount,
        f.discount_percent,
        f.quantity,
        p.category,
        d.year,
        d.month,
        d.month_name,
        STR_TO_DATE(CONCAT(d.year, '-', LPAD(d.month, 2, '0'), '-01'), '%Y-%m-%d')
                                                                        AS month_start_date,
        -- Discount bands per business rules
        CASE
            WHEN f.discount_percent <= 5  THEN '0-5%'
            WHEN f.discount_percent <= 10 THEN '5-10%'
            WHEN f.discount_percent <= 20 THEN '10-20%'
            ELSE '20%+'
        END                                                             AS discount_band,
        f.gross_revenue - f.net_revenue                                 AS revenue_lost_to_discount
    FROM fact_sales AS f
    INNER JOIN dim_product AS p ON f.product_key = p.product_key
    INNER JOIN dim_date AS d ON f.date_key = d.date_key
)
SELECT
    year,
    month,
    month_name,
    month_start_date,
    discount_band,
    category,
    COUNT(DISTINCT order_line_id)                                       AS order_line_count,
    COUNT(DISTINCT order_id)                                            AS order_count,
    SUM(quantity)                                                       AS units_sold,
    SUM(gross_revenue)                                                  AS gross_revenue,
    SUM(net_revenue)                                                    AS net_revenue,
    SUM(revenue_lost_to_discount)                                        AS revenue_lost_to_discounts,
    SUM(gross_profit)                                                   AS gross_profit,
    ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(net_revenue), 0), 2)   AS profit_margin_pct,
    ROUND(AVG(discount_percent), 2)                                      AS avg_discount_pct,
  -- Discount depth vs margin: negative slope expected on heavily discounted lines
    ROUND(
        100.0 * SUM(revenue_lost_to_discount) / NULLIF(SUM(gross_revenue), 0),
        2
    )                                                                   AS discount_penetration_pct,
    ROUND(SUM(gross_profit) / NULLIF(COUNT(DISTINCT order_line_id), 0), 2)
                                                                        AS profit_per_line
FROM line_enriched
GROUP BY
    year, month, month_name, month_start_date, discount_band, category;
