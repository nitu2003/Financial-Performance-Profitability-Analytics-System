-- =============================================================================
-- metric_yoy_growth.sql
-- Year-over-year (YoY) growth by matching calendar month across years.
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW vw_metric_yoy_growth AS
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
prior_year AS (
    SELECT
        cur.year,
        cur.month,
        cur.month_name,
        cur.month_start_date,
        cur.year_month_key,
        cur.net_revenue,
        py.net_revenue                                                    AS prior_year_revenue,
        cur.gross_profit,
        py.gross_profit                                                   AS prior_year_profit,
        cur.order_count,
        py.order_count                                                    AS prior_year_orders,
        cur.average_order_value,
        py.average_order_value                                            AS prior_year_aov
    FROM monthly AS cur
    LEFT JOIN monthly AS py
        ON cur.month = py.month
       AND cur.year = py.year + 1
)
SELECT
    year,
    month,
    month_name,
    month_start_date,
    year_month_key,
    net_revenue,
    prior_year_revenue,
    gross_profit,
    prior_year_profit,
    order_count,
    prior_year_orders,
    average_order_value,
    prior_year_aov,
    ROUND(100.0 * (net_revenue - prior_year_revenue) / NULLIF(prior_year_revenue, 0), 2)
                                                                        AS revenue_yoy_growth_pct,
    ROUND(100.0 * (gross_profit - prior_year_profit) / NULLIF(prior_year_profit, 0), 2)
                                                                        AS profit_yoy_growth_pct,
    ROUND(100.0 * (order_count - prior_year_orders) / NULLIF(prior_year_orders, 0), 2)
                                                                        AS orders_yoy_growth_pct,
    ROUND(100.0 * (average_order_value - prior_year_aov) / NULLIF(prior_year_aov, 0), 2)
                                                                        AS aov_yoy_growth_pct
FROM prior_year;
