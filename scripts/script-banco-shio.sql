-- ============================================================
-- SCRIPT FÍSICO FINAL: E-COMMERCE SHIO
-- Banco de Dados: PostgreSQL
-- Última alteração: 19/05/2026
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS (Tipos de Dados Padronizados)
-- ============================================================
CREATE TYPE user_role AS ENUM ('CUSTOMER', 'ADMIN', 'INVENTORY_MANAGER');
CREATE TYPE order_status AS ENUM ('AWAITING_PAYMENT', 'PAID', 'PREPARING', 'SHIPPED', 'DELIVERED', 'CANCELED');
CREATE TYPE payment_method AS ENUM ('PIX', 'CREDIT_CARD', 'BOLETO');
CREATE TYPE payment_status AS ENUM ('PENDING', 'PROCESSING', 'PAID', 'FAILED', 'REFUNDED');

-- ============================================================
-- 1. AUTENTICAÇÃO E PERFIL (Integração Django)
-- ============================================================
CREATE TABLE authentication_user (
    id              BIGSERIAL PRIMARY KEY,
    password        VARCHAR(128) NOT NULL,
    last_login      TIMESTAMPTZ,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    first_name      VARCHAR(150) NOT NULL DEFAULT '',
    last_name       VARCHAR(150) NOT NULL DEFAULT '',
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    email           VARCHAR(254) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    google_id       VARCHAR(255) UNIQUE,
    avatar_url      TEXT,
    is_new_user     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_profile (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id    BIGINT NOT NULL UNIQUE REFERENCES authentication_user(id) ON DELETE CASCADE,
    phone_number    VARCHAR(20),
    cpf             VARCHAR(14) UNIQUE,
    role            user_role NOT NULL DEFAULT 'CUSTOMER',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE address (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL REFERENCES authentication_user(id) ON DELETE CASCADE,
    title           VARCHAR(50) DEFAULT 'Home',
    zip_code        VARCHAR(9) NOT NULL,
    street          VARCHAR(255) NOT NULL,
    address_number  VARCHAR(20) NOT NULL,
    complement      VARCHAR(100),
    neighborhood    VARCHAR(100) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    state           CHAR(2) NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. CATÁLOGO, PRODUTOS E VARIAÇÕES
-- ============================================================
CREATE TABLE category (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL UNIQUE, 
    slug            VARCHAR(150) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE drop_campaign (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    launch_date     TIMESTAMPTZ,
    end_date        TIMESTAMPTZ, 
    max_quantity    INTEGER,
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drop_id             UUID REFERENCES drop_campaign(id) ON DELETE SET NULL,
    category_id         UUID REFERENCES category(id) ON DELETE SET NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    base_price          NUMERIC(10,2) NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product_variation (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    size            VARCHAR(50) NOT NULL,
    sku             VARCHAR(100) UNIQUE,
    stock_quantity  INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product_image (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id    UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    url           TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. CARRINHO (Usuários Logados)
-- ============================================================
-- Carrinhos anônimos serão gerenciados no cache do Redis e salvos
-- nesta tabela apenas após a autenticação do usuário.
CREATE TABLE cart (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT NOT NULL REFERENCES authentication_user(id) ON DELETE CASCADE,
    status      VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'FINISHED', 'ABANDONED')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE cart_item (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id         UUID NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
    variation_id    UUID NOT NULL REFERENCES product_variation(id) ON DELETE CASCADE,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10,2) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE coupon (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(50) NOT NULL UNIQUE,
    discount_type   VARCHAR(20) NOT NULL CHECK (discount_type IN ('PERCENTAGE', 'FIXED_VALUE')),
    discount_value  NUMERIC(10,2) NOT NULL,
    expiration_date TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. PEDIDOS E PAGAMENTOS (Integração HyperCash futuramente)
-- ============================================================
CREATE TABLE customer_order (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             BIGINT NOT NULL REFERENCES authentication_user(id) ON DELETE RESTRICT,
    address_id          UUID REFERENCES address(id) ON DELETE SET NULL,
    coupon_id           UUID REFERENCES coupon(id) ON DELETE SET NULL,
    status              order_status NOT NULL DEFAULT 'AWAITING_PAYMENT',
    subtotal            NUMERIC(10,2) NOT NULL,
    shipping_cost       NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount     NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_amount        NUMERIC(10,2) NOT NULL,
    tracking_code       VARCHAR(100),
    shipping_zip_code   VARCHAR(9) NOT NULL,
    shipping_street     VARCHAR(255) NOT NULL,
    shipping_number     VARCHAR(20) NOT NULL,
    shipping_complement VARCHAR(100),
    shipping_neighborhood VARCHAR(100) NOT NULL,
    shipping_city       VARCHAR(100) NOT NULL,
    shipping_state      CHAR(2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_item (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES customer_order(id) ON DELETE CASCADE,
    variation_id    UUID REFERENCES product_variation(id) ON DELETE SET NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10,2) NOT NULL,
    product_name    VARCHAR(255) NOT NULL,
    sku_snapshot    VARCHAR(100),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE payment (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id                UUID NOT NULL UNIQUE REFERENCES customer_order(id) ON DELETE CASCADE,
    method                  payment_method NOT NULL,
    status                  payment_status NOT NULL DEFAULT 'PENDING',
    total_amount            NUMERIC(10,2) NOT NULL,
    installments            INTEGER NOT NULL DEFAULT 1,
    installment_value       NUMERIC(10,2),
    gateway_transaction_id  VARCHAR(255) UNIQUE,
    qrcode_pix              TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);