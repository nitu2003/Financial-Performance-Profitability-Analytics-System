-- =============================================================================
-- mart_loss_making_products.sql
-- Products with negative gross profit — alert and remediation list.
-- Grain: product_key (aggregated over full fact period) + monthly detail view
-- =============================================================================

USE financial_analytics;

-- Lifetime / full-period loss-making product summary
CREATE OR REPLACE VIEW mart_loss_making_products AS
WITH product_totals AS (
    SELECT
        p.product_key,
        p.product_id,
        p.product_name,
        p.category,
        p.unit_cost,
        p.unit_price,
        SUM(f.net_revenue)                                              AS net_revenue,
        SUM(f.gross_revenue)                                            AS gross_revenue,
        SUM(f.gross_profit)                                             AS gross_profit,
        SUM(f.discount_amount)                                          AS total_discount_impact,
        SUM(f.quantity)                                                 AS units_sold,
        COUNT(DISTINCT f.order_id)                                      AS order_count,
        ROUND(AVG(f.discount_percent), 2)                               AS avg_discount_pct,
        MIN(d.full_date)                                                AS first_sale_date,
        MAX(d.full_date)                                                AS last_sale_date
    FROM fact_sales AS f
    INNER JOIN dim_product AS p ON f.product_key = p.product_key
    INNER JOIN dim_date AS d ON f.date_key = d.date_key
    GROUP BY
        p.product_key, p.product_id, p.product_name, p.category,
        p.unit_cost, p.unit_price
    HAVING SUM(f.gross_profit) < 0
),
ranked AS (
    SELECT
        pt.*,
        ROUND(100.0 * pt.gross_profit / NULLIF(pt.net_revenue, 0), 2)  AS profit_margin_pct,
        RANK() OVER (ORDER BY pt.gross_profit ASC)                      AS loss_severity_rank,
        RANK() OVER (ORDER BY pt.net_revenue DESC)                      AS revenue_rank
    FROM product_totals AS pt
)
SELECT
    product_key,
    product_id,
    product_name,
    category,
    unit_cost,
    unit_price,
    net_revenue,
    gross_revenue,
    gross_profit,
    profit_margin_pct,
    total_discount_impact,
    units_sold,
    order_count,
    avg_discount_pct,
    first_sale_date,
    last_sale_date,
    loss_severity_rank,
    revenue_rank,
    CASE
        WHEN profit_margin_pct <= -10 THEN 'Critical Loss'
        WHEN profit_margin_pct <= -5  THEN 'Severe Loss'
        ELSE 'Moderate Loss'
    END                                                                 AS loss_severity_band
FROM ranked;


-- Monthly loss-making detail for trend / remediation tracking
CREATE OR REPLACE VIEW mart_loss_making_products_monthly AS
SELECT
    mp.product_key,
    mp.product_id,
    mp.product_name,
    mp.category,
    mp.year,
    mp.month,
    mp.month_name,
    mp.month_start_date,
    mp.net_revenue,
    mp.gross_profit,
    mp.profit_margin_pct,
    mp.total_quantity_sold                                              AS units_sold,
    mp.total_discount_amount                                            AS total_discount_impact,
    mp.avg_discount_pct,
    mp.profitability_flag
FROM mart_product_profitability AS mp
WHERE mp.is_loss_making = 1;
