-- =============================================================================
-- metric_profit_margin.sql
-- Profit and margin KPIs derived from the monthly sales metric view.
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW vw_metric_profit_margin AS
SELECT
    year,
    month,
    month_name,
    month_start_date,
    year_month_key,
    net_revenue,
    gross_profit,
    gross_revenue,
    total_cogs,
    total_discount_amount,
    -- Profit margin % on net revenue (safe divide)
    ROUND(100.0 * gross_profit / NULLIF(net_revenue, 0), 2)             AS profit_margin_pct,
    -- Discount as % of gross revenue
    ROUND(100.0 * total_discount_amount / NULLIF(gross_revenue, 0), 2)  AS discount_rate_pct,
    -- COGS as % of net revenue
    ROUND(100.0 * total_cogs / NULLIF(net_revenue, 0), 2)               AS cogs_pct_of_revenue,
    order_count,
    customer_count
FROM vw_metric_sales_monthly;
