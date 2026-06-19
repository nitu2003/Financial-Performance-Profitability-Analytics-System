-- =============================================================================
-- mart_monthly_trends.sql
-- Executive monthly KPI trend mart (company-wide).
-- Grain: year + month
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW mart_monthly_trends AS
SELECT
    m.year,
    m.month,
    m.month_name,
    m.month_start_date,
    m.year_month_key,
    m.gross_revenue,
    m.total_discount_amount,
    m.net_revenue,
    m.gross_profit,
    pm.profit_margin_pct,
    pm.discount_rate_pct,
    m.order_count,
    m.customer_count,
    m.order_line_count,
    m.units_sold,
    a.average_order_value,
    a.average_profit_per_order,
    a.average_units_per_order,
    mom.revenue_mom_growth_pct,
    mom.profit_mom_growth_pct,
    mom.orders_mom_growth_pct,
    mom.aov_mom_growth_pct,
    yoy.revenue_yoy_growth_pct,
    yoy.profit_yoy_growth_pct,
    yoy.orders_yoy_growth_pct,
    yoy.aov_yoy_growth_pct
FROM vw_metric_sales_monthly AS m
LEFT JOIN vw_metric_profit_margin AS pm
    ON m.year = pm.year AND m.month = pm.month
LEFT JOIN vw_metric_aov AS a
    ON m.year = a.year AND m.month = a.month
LEFT JOIN vw_metric_mom_growth AS mom
    ON m.year = mom.year AND m.month = mom.month
LEFT JOIN vw_metric_yoy_growth AS yoy
    ON m.year = yoy.year AND m.month = yoy.month;
