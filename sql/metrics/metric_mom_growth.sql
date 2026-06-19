-- =============================================================================
-- metric_mom_growth.sql
-- Month-over-month (MoM) growth for revenue, profit, orders, and AOV.
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW vw_metric_mom_growth AS
WITH monthly AS (
    SELECT
        year,
        month,
        month_name,
        month_start_date,
        year_month_key,
        net_revenue,
        gross_profit,
        order_count,
        ROUND(net_revenue / NULLIF(order_count, 0), 2)                  AS average_order_value
    FROM vw_metric_sales_monthly
),
lagged AS (
    SELECT
        m.*,
        LAG(net_revenue) OVER (ORDER BY year, month)                    AS prior_month_revenue,
        LAG(gross_profit) OVER (ORDER BY year, month)                   AS prior_month_profit,
        LAG(order_count) OVER (ORDER BY year, month)                    AS prior_month_orders,
        LAG(average_order_value) OVER (ORDER BY year, month)            AS prior_month_aov
    FROM monthly AS m
)
SELECT
    year,
    month,
    month_name,
    month_start_date,
    year_month_key,
    net_revenue,
    prior_month_revenue,
    gross_profit,
    prior_month_profit,
    order_count,
    prior_month_orders,
    average_order_value,
    prior_month_aov,
    ROUND(100.0 * (net_revenue - prior_month_revenue) / NULLIF(prior_month_revenue, 0), 2)
                                                                        AS revenue_mom_growth_pct,
    ROUND(100.0 * (gross_profit - prior_month_profit) / NULLIF(prior_month_profit, 0), 2)
                                                                        AS profit_mom_growth_pct,
    ROUND(100.0 * (order_count - prior_month_orders) / NULLIF(prior_month_orders, 0), 2)
                                                                        AS orders_mom_growth_pct,
    ROUND(100.0 * (average_order_value - prior_month_aov) / NULLIF(prior_month_aov, 0), 2)
                                                                        AS aov_mom_growth_pct
FROM lagged;
