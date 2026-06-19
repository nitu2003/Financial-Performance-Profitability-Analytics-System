-- =============================================================================
-- metric_revenue.sql
-- Reusable monthly revenue base view for KPI and growth metrics.
-- Grain: year + month (company-wide)
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW vw_metric_sales_monthly AS
SELECT
    d.year,
    d.month,
    MIN(d.month_name)                                                   AS month_name,
    STR_TO_DATE(CONCAT(d.year, '-', LPAD(d.month, 2, '0'), '-01'), '%Y-%m-%d') AS month_start_date,
    CAST(CONCAT(d.year, LPAD(d.month, 2, '0')) AS UNSIGNED)             AS year_month_key,
    SUM(f.gross_revenue)                                                AS gross_revenue,
    SUM(f.discount_amount)                                              AS total_discount_amount,
    SUM(f.net_revenue)                                                  AS net_revenue,
    SUM(f.cogs)                                                         AS total_cogs,
    SUM(f.gross_profit)                                                 AS gross_profit,
    COUNT(DISTINCT f.order_id)                                          AS order_count,
    COUNT(DISTINCT f.customer_key)                                      AS customer_count,
    COUNT(DISTINCT f.order_line_id)                                     AS order_line_count,
    SUM(f.quantity)                                                     AS units_sold
FROM fact_sales AS f
INNER JOIN dim_date AS d ON f.date_key = d.date_key
GROUP BY d.year, d.month;


CREATE OR REPLACE VIEW vw_metric_revenue AS
SELECT
    year,
    month,
    month_name,
    month_start_date,
    year_month_key,
    gross_revenue,
    total_discount_amount,
    net_revenue,
    total_cogs,
    gross_profit,
    order_count,
    customer_count,
    order_line_count,
    units_sold
FROM vw_metric_sales_monthly;
