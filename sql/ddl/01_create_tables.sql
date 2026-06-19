-- =============================================================================
-- Financial Performance & Profitability Analytics — MySQL warehouse DDL
-- Database: financial_analytics (configured in python/config.py)
-- Layers: staging (CSV mirror) → dimensions → fact_sales (order-line grain)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS financial_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE financial_analytics;

-- ---------------------------------------------------------------------------
-- Staging tables (normalized mirrors of sources/*.csv)
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS fact_sales;

DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_region;

DROP TABLE IF EXISTS stg_order_lines;
DROP TABLE IF EXISTS stg_orders;
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_products;
DROP TABLE IF EXISTS stg_regions;

CREATE TABLE stg_regions (
    region_id     VARCHAR(20)   NOT NULL,
    region_name   VARCHAR(100)  NOT NULL,
    country       VARCHAR(100)  NOT NULL,
    PRIMARY KEY (region_id)
) ENGINE=InnoDB;

CREATE TABLE stg_products (
    product_id    VARCHAR(20)   NOT NULL,
    product_name  VARCHAR(200)  NOT NULL,
    category      VARCHAR(50)   NOT NULL,
    unit_cost     DECIMAL(12, 2) NOT NULL,
    unit_price    DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (product_id)
) ENGINE=InnoDB;

CREATE TABLE stg_customers (
    customer_id   VARCHAR(20)   NOT NULL,
    customer_name VARCHAR(200)  NOT NULL,
    segment       VARCHAR(50)   NOT NULL,
    join_date     DATE          NOT NULL,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB;

CREATE TABLE stg_orders (
    order_id      VARCHAR(20)   NOT NULL,
    customer_id   VARCHAR(20)   NOT NULL,
    order_date    DATE          NOT NULL,
    region_id     VARCHAR(20)   NOT NULL,
    PRIMARY KEY (order_id),
    INDEX idx_stg_orders_customer (customer_id),
    INDEX idx_stg_orders_region (region_id),
    INDEX idx_stg_orders_date (order_date)
) ENGINE=InnoDB;

CREATE TABLE stg_order_lines (
    order_line_id    VARCHAR(20)   NOT NULL,
    order_id         VARCHAR(20)   NOT NULL,
    product_id       VARCHAR(20)   NOT NULL,
    quantity         INT           NOT NULL,
    unit_price       DECIMAL(12, 2) NOT NULL,
    discount_percent DECIMAL(5, 2)  NOT NULL DEFAULT 0,
    unit_cost        DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (order_line_id),
    UNIQUE KEY uq_stg_order_lines (order_line_id),
    INDEX idx_stg_lines_order (order_id),
    INDEX idx_stg_lines_product (product_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Dimension tables (surrogate keys)
-- ---------------------------------------------------------------------------

CREATE TABLE dim_region (
    region_key    INT AUTO_INCREMENT NOT NULL,
    region_id     VARCHAR(20)   NOT NULL,
    region_name   VARCHAR(100)  NOT NULL,
    country       VARCHAR(100)  NOT NULL,
    PRIMARY KEY (region_key),
    UNIQUE KEY uq_dim_region_natural (region_id)
) ENGINE=InnoDB;

CREATE TABLE dim_product (
    product_key   INT AUTO_INCREMENT NOT NULL,
    product_id    VARCHAR(20)   NOT NULL,
    product_name  VARCHAR(200)  NOT NULL,
    category      VARCHAR(50)   NOT NULL,
    unit_cost     DECIMAL(12, 2) NOT NULL,
    unit_price    DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (product_key),
    UNIQUE KEY uq_dim_product_natural (product_id),
    INDEX idx_dim_product_category (category)
) ENGINE=InnoDB;

CREATE TABLE dim_customer (
    customer_key   INT AUTO_INCREMENT NOT NULL,
    customer_id    VARCHAR(20)   NOT NULL,
    customer_name  VARCHAR(200)  NOT NULL,
    segment        VARCHAR(50)   NOT NULL,
    join_date      DATE          NOT NULL,
    PRIMARY KEY (customer_key),
    UNIQUE KEY uq_dim_customer_natural (customer_id),
    INDEX idx_dim_customer_segment (segment)
) ENGINE=InnoDB;

CREATE TABLE dim_date (
    date_key      INT          NOT NULL,
    full_date     DATE         NOT NULL,
    year          SMALLINT     NOT NULL,
    quarter       TINYINT      NOT NULL,
    month         TINYINT      NOT NULL,
    month_name    VARCHAR(20)  NOT NULL,
    day_of_month  TINYINT      NOT NULL,
    day_of_week   TINYINT      NOT NULL,
    day_name      VARCHAR(20)  NOT NULL,
    is_weekend    TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (date_key),
    UNIQUE KEY uq_dim_date_full (full_date),
    INDEX idx_dim_date_year_month (year, month)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Fact table — order-line grain
-- ---------------------------------------------------------------------------

CREATE TABLE fact_sales (
    order_line_id    VARCHAR(20)    NOT NULL,
    order_id         VARCHAR(20)    NOT NULL,
    date_key         INT            NOT NULL,
    customer_key     INT            NOT NULL,
    product_key      INT            NOT NULL,
    region_key       INT            NOT NULL,
    quantity         INT            NOT NULL,
    unit_price       DECIMAL(12, 2) NOT NULL,
    unit_cost        DECIMAL(12, 2) NOT NULL,
    discount_percent DECIMAL(5, 2)  NOT NULL DEFAULT 0,
    gross_revenue    DECIMAL(14, 2) NOT NULL,
    discount_amount  DECIMAL(14, 2) NOT NULL,
    net_revenue      DECIMAL(14, 2) NOT NULL,
    cogs             DECIMAL(14, 2) NOT NULL,
    gross_profit     DECIMAL(14, 2) NOT NULL,
    PRIMARY KEY (order_line_id),
    INDEX idx_fact_order (order_id),
    INDEX idx_fact_date (date_key),
    INDEX idx_fact_customer (customer_key),
    INDEX idx_fact_product (product_key),
    INDEX idx_fact_region (region_key),
    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_key) REFERENCES dim_date (date_key),
    CONSTRAINT fk_fact_customer
        FOREIGN KEY (customer_key) REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fact_product
        FOREIGN KEY (product_key) REFERENCES dim_product (product_key),
    CONSTRAINT fk_fact_region
        FOREIGN KEY (region_key) REFERENCES dim_region (region_key)
) ENGINE=InnoDB;
