CREATE DATABASE IF NOT EXISTS fraud_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE fraud_analytics;

CREATE TABLE IF NOT EXISTS merchants (
    merchant_id       INT           NOT NULL,
    merchant_name     VARCHAR(200)  NOT NULL,
    category          VARCHAR(100)  NOT NULL,
    country           CHAR(2)       NOT NULL,
    mcc_code          SMALLINT      NOT NULL,
    onboarded_date    DATE          NOT NULL,
    is_high_risk      TINYINT(1)    NOT NULL DEFAULT 0,
    PRIMARY KEY (merchant_id),
    INDEX idx_merchants_category (category),
    INDEX idx_merchants_risk (is_high_risk)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INT          NOT NULL,
    name          VARCHAR(200) NOT NULL,
    email         VARCHAR(200) NOT NULL,
    country       CHAR(2)      NOT NULL,
    card_type     VARCHAR(20)  NOT NULL,
    created_at    DATE         NOT NULL,
    PRIMARY KEY (customer_id),
    INDEX idx_customers_country (country)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id    INT            NOT NULL,
    merchant_id       INT            NOT NULL,
    customer_id       INT            NOT NULL,
    amount            DECIMAL(12,2)  NOT NULL,
    currency          CHAR(3)        NOT NULL DEFAULT 'USD',
    status            VARCHAR(20)    NOT NULL,
    txn_datetime      DATETIME       NOT NULL,
    hour_of_day       TINYINT        NOT NULL,
    ip_country        CHAR(2)        NOT NULL,
    billing_country   CHAR(2)        NOT NULL,
    location_mismatch TINYINT(1)     NOT NULL DEFAULT 0,
    is_fraud          TINYINT(1)     NOT NULL DEFAULT 0,
    PRIMARY KEY (transaction_id),
    INDEX idx_txn_merchant   (merchant_id),
    INDEX idx_txn_customer   (customer_id),
    INDEX idx_txn_datetime   (txn_datetime),
    INDEX idx_txn_status     (status),
    INDEX idx_txn_is_fraud   (is_fraud),
    CONSTRAINT fk_txn_merchant  FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id),
    CONSTRAINT fk_txn_customer  FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id       INT           NOT NULL,
    transaction_id  INT           NOT NULL,
    merchant_id     INT           NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    refund_date     DATE          NOT NULL,
    reason          VARCHAR(50)   NOT NULL,
    status          VARCHAR(20)   NOT NULL,
    PRIMARY KEY (refund_id),
    INDEX idx_refund_transaction (transaction_id),
    INDEX idx_refund_merchant    (merchant_id),
    CONSTRAINT fk_refund_txn       FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id),
    CONSTRAINT fk_refund_merchant  FOREIGN KEY (merchant_id)    REFERENCES merchants (merchant_id)
);

CREATE TABLE IF NOT EXISTS chargebacks (
    chargeback_id        INT            NOT NULL,
    transaction_id       INT            NOT NULL,
    merchant_id          INT            NOT NULL,
    customer_id          INT            NOT NULL,
    disputed_amount      DECIMAL(12,2)  NOT NULL,
    reason_code          VARCHAR(20)    NOT NULL,
    reason_description   VARCHAR(200)   NOT NULL,
    chargeback_type      VARCHAR(20)    NOT NULL,
    stage                VARCHAR(30)    NOT NULL,
    stage_date           DATE           NOT NULL,
    deadline_date        DATE           NOT NULL,
    outcome              VARCHAR(20)    NOT NULL,
    is_final_stage       TINYINT(1)     NOT NULL DEFAULT 0,
    arbitration_fee      DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    loss_amount          DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    is_fraud_transaction TINYINT(1)     NOT NULL DEFAULT 0,
    PRIMARY KEY (chargeback_id),
    INDEX idx_cb_transaction (transaction_id),
    INDEX idx_cb_merchant    (merchant_id),
    INDEX idx_cb_stage       (stage),
    INDEX idx_cb_outcome     (outcome),
    INDEX idx_cb_final       (is_final_stage),
    INDEX idx_cb_reason      (reason_code),
    CONSTRAINT fk_cb_txn       FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id),
    CONSTRAINT fk_cb_merchant  FOREIGN KEY (merchant_id)    REFERENCES merchants (merchant_id),
    CONSTRAINT fk_cb_customer  FOREIGN KEY (customer_id)    REFERENCES customers (customer_id)
);
