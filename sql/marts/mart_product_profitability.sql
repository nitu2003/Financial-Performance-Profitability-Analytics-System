-- =============================================================================
-- mart_product_profitability.sql
-- Product and category profitability by month with performance flags.
-- Grain: product_key + year + month
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW mart_product_profitability AS
WITH product_monthly AS (
    SELECT
        p.product_key,
        p.product_id,
        p.product_name,
        p.category,
        p.unit_cost,
        p.unit_price,
        d.year,
        d.month,
        MIN(d.month_name)                                               AS month_name,
        STR_TO_DATE(CONCAT(d.year, '-', LPAD(d.month, 2, '0'), '-01'), '%Y-%m-%d')
                                                                        AS month_start_date,
        SUM(f.net_revenue)                                              AS net_revenue,
        SUM(f.gross_profit)                                             AS gross_profit,
        SUM(f.gross_revenue)                                            AS gross_revenue,
        SUM(f.discount_amount)                                          AS total_discount_amount,
        SUM(f.quantity)                                                 AS total_quantity_sold,
        COUNT(DISTINCT f.order_id)                                      AS order_count,
        ROUND(AVG(f.discount_percent), 2)                               AS avg_discount_pct
    FROM fact_sales AS f
    INNER JOIN dim_product AS p ON f.product_key = p.product_key
    INNER JOIN dim_date AS d ON f.date_key = d.date_key
    GROUP BY
        p.product_key, p.product_id, p.product_name, p.category,
        p.unit_cost, p.unit_price, d.year, d.month
),
scored AS (
    SELECT
        pm.*,
        ROUND(100.0 * pm.gross_profit / NULLIF(pm.net_revenue, 0), 2)    AS profit_margin_pct,
        -- Revenue rank within category-month (1 = highest revenue)
        RANK() OVER (
            PARTITION BY pm.category, pm.year, pm.month
            ORDER BY pm.net_revenue DESC
        )                                                               AS revenue_rank_in_category,
        COUNT(*) OVER (
            PARTITION BY pm.category, pm.year, pm.month
        )                                                               AS products_in_category_month
    FROM product_monthly AS pm
)
SELECT
    product_key,
    product_id,
    product_name,
    category,
    unit_cost,
    unit_price,
    year,
    month,
    month_name,
    month_start_date,
    net_revenue,
    gross_revenue,
    gross_profit,
    profit_margin_pct,
    total_quantity_sold,
    total_discount_amount,
    avg_discount_pct,
    order_count,
    revenue_rank_in_category,
    -- Loss-making: negative contribution profit in the period
    CASE WHEN gross_profit < 0 THEN 1 ELSE 0 END                        AS is_loss_making,
    -- High revenue + low margin: top 25% revenue in category-month AND margin below 8%
    CASE
        WHEN revenue_rank_in_category <= CEIL(products_in_category_month * 0.25)
         AND profit_margin_pct < 8
        THEN 1
        ELSE 0
    END                                                                 AS is_high_revenue_low_margin,
    CASE
        WHEN gross_profit < 0 THEN 'Loss Making'
        WHEN revenue_rank_in_category <= CEIL(products_in_category_month * 0.25)
         AND profit_margin_pct < 8
        THEN 'High Revenue Low Margin'
        WHEN profit_margin_pct >= 25 THEN 'High Margin'
        ELSE 'Standard'
    END                                                                 AS profitability_flag
FROM scored;
