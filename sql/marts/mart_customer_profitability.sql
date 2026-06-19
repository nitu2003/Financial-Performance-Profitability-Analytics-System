-- =============================================================================
-- mart_customer_profitability.sql
-- Customer-level profitability, AOV, frequency, and value segmentation.
-- Grain: customer_key (lifetime over loaded fact period)
-- =============================================================================

USE financial_analytics;

CREATE OR REPLACE VIEW mart_customer_profitability AS
WITH customer_metrics AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.customer_name,
        c.segment                                                         AS customer_segment,
        c.join_date,
        MIN(d.full_date)                                                  AS first_order_date,
        MAX(d.full_date)                                                  AS last_order_date,
        COUNT(DISTINCT f.order_id)                                        AS total_orders,
        SUM(f.net_revenue)                                                AS total_spend,
        SUM(f.gross_profit)                                               AS total_profit_contribution,
        SUM(f.discount_amount)                                            AS total_discount_received,
        SUM(f.quantity)                                                   AS total_units_purchased,
        COUNT(DISTINCT d.year * 100 + d.month)                          AS active_months
    FROM fact_sales AS f
    INNER JOIN dim_customer AS c ON f.customer_key = c.customer_key
    INNER JOIN dim_date AS d ON f.date_key = d.date_key
    GROUP BY
        c.customer_key, c.customer_id, c.customer_name, c.segment, c.join_date
),
enriched AS (
    SELECT
        cm.*,
        DATEDIFF(cm.last_order_date, cm.first_order_date)                 AS customer_tenure_days,
        ROUND(cm.total_spend / NULLIF(cm.total_orders, 0), 2)           AS average_order_value,
        -- Simple historical CLV approximation = total net revenue in period
        ROUND(cm.total_spend, 2)                                          AS customer_lifetime_value_approx,
        ROUND(cm.total_profit_contribution / NULLIF(cm.total_orders, 0), 2)
                                                                        AS avg_profit_per_order,
        ROUND(
            cm.total_orders / NULLIF(
                GREATEST(1, TIMESTAMPDIFF(MONTH, cm.first_order_date, cm.last_order_date) + 1),
                0
            ),
            2
        )                                                                 AS orders_per_month,
        ROUND(100.0 * cm.total_profit_contribution / NULLIF(cm.total_spend, 0), 2)
                                                                        AS profit_margin_pct,
        NTILE(3) OVER (ORDER BY cm.total_spend DESC)                      AS value_tertile
    FROM customer_metrics AS cm
)
SELECT
    customer_key,
    customer_id,
    customer_name,
    customer_segment,
    join_date,
    first_order_date,
    last_order_date,
    customer_tenure_days,
    total_orders,
    total_spend,
    total_profit_contribution,
    total_discount_received,
    total_units_purchased,
    active_months,
    average_order_value,
    customer_lifetime_value_approx,
    avg_profit_per_order,
    orders_per_month,
    profit_margin_pct,
    CASE value_tertile
        WHEN 1 THEN 'High Value'
        WHEN 2 THEN 'Medium Value'
        ELSE 'Low Value'
    END                                                                 AS customer_value_segment,
    value_tertile
FROM enriched;
