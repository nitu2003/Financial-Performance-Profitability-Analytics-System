-- =============================================================================
-- metric_aov.sql
-- Average order value (AOV) by month.
-- AOV = net revenue / distinct orders
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW vw_metric_aov AS
SELECT
    year,
    month,
    month_name,
    month_start_date,
    year_month_key,
    net_revenue,
    order_count,
    ROUND(net_revenue / NULLIF(order_count, 0), 2)                      AS average_order_value,
    ROUND(gross_profit / NULLIF(order_count, 0), 2)                     AS average_profit_per_order,
    ROUND(units_sold / NULLIF(order_count, 0), 2)                       AS average_units_per_order
FROM vw_metric_sales_monthly;
