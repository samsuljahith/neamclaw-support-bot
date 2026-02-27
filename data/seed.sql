-- ============================================================================
-- TechNova Support Bot — Database Schema & Seed Data
-- Run: sqlite3 ./data/technova.db < data/seed.sql
-- ============================================================================

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    phone       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    price           REAL NOT NULL,
    stock_quantity  INTEGER NOT NULL DEFAULT 0,
    description     TEXT
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    status          TEXT NOT NULL DEFAULT 'pending',
    total_amount    REAL NOT NULL,
    tracking_number TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    shipped_at      TEXT,
    delivered_at    TEXT
);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT NOT NULL REFERENCES orders(id),
    product_id  TEXT NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    unit_price  REAL NOT NULL
);

-- =========== SEED DATA ===========

-- Customers
INSERT INTO customers (id, name, email, phone) VALUES
    ('C001', 'Alice Johnson',   'alice@example.com',    '+1-555-0101'),
    ('C002', 'Bob Martinez',    'bob.m@example.com',    '+1-555-0102'),
    ('C003', 'Carol Chen',      'carol.chen@example.com', '+1-555-0103'),
    ('C004', 'David Kim',       'david.k@example.com',  '+1-555-0104'),
    ('C005', 'Eva Patel',       'eva.patel@example.com', '+1-555-0105');

-- Products
INSERT INTO products (id, name, category, price, stock_quantity, description) VALUES
    ('P001', 'TechNova Pro Wireless Earbuds',     'Audio',       79.99,  150, 'Active noise cancellation, 30hr battery, IPX5 waterproof'),
    ('P002', 'TechNova UltraCharge Power Bank',    'Accessories', 49.99,  200, '20000mAh, USB-C PD 65W, charges 3 devices simultaneously'),
    ('P003', 'TechNova SmartWatch X1',             'Wearables',   199.99, 75,  'AMOLED display, heart rate, SpO2, GPS, 5-day battery'),
    ('P004', 'TechNova 4K Webcam',                 'Peripherals', 129.99, 50,  '4K/30fps, auto-focus, built-in ring light, USB-C'),
    ('P005', 'TechNova Mechanical Keyboard K7',    'Peripherals', 89.99,  120, 'Hot-swappable switches, RGB, aluminum frame, wireless'),
    ('P006', 'TechNova USB-C Hub 9-in-1',          'Accessories', 59.99,  180, 'HDMI 4K, SD/microSD, USB 3.0 x3, Ethernet, PD 100W'),
    ('P007', 'TechNova Noise-Canceling Headphones', 'Audio',      149.99, 90,  'Over-ear, ANC, 40hr battery, multipoint Bluetooth'),
    ('P008', 'TechNova Portable SSD 1TB',          'Storage',     89.99,  60,  'USB 3.2 Gen2, 1050MB/s read, shock-resistant, encrypted'),
    ('P009', 'TechNova Smart LED Desk Lamp',       'Home',        69.99,  100, 'Wireless charging base, 5 color temps, auto-brightness'),
    ('P010', 'TechNova Laptop Stand Pro',           'Accessories', 39.99,  0,   'Aluminum, adjustable height, foldable, supports up to 17"');

-- Orders
INSERT INTO orders (id, customer_id, status, total_amount, tracking_number, created_at, shipped_at, delivered_at) VALUES
    ('ORD-10001', 'C001', 'delivered',  129.98, 'TRK-AA-001', '2026-01-15 10:30:00', '2026-01-16 08:00:00', '2026-01-21 14:30:00'),
    ('ORD-10002', 'C002', 'shipped',    199.99, 'TRK-BB-002', '2026-02-20 14:45:00', '2026-02-21 09:00:00', NULL),
    ('ORD-10003', 'C001', 'processing', 89.99,  NULL,         '2026-02-25 09:00:00', NULL,                  NULL),
    ('ORD-10004', 'C003', 'delivered',  259.98, 'TRK-CC-003', '2026-01-28 11:20:00', '2026-01-29 08:30:00', '2026-02-03 16:00:00'),
    ('ORD-10005', 'C004', 'cancelled',  79.99,  NULL,         '2026-02-10 16:00:00', NULL,                  NULL),
    ('ORD-10006', 'C005', 'shipped',    219.98, 'TRK-DD-004', '2026-02-22 08:15:00', '2026-02-23 07:00:00', NULL),
    ('ORD-10007', 'C002', 'pending',    149.99, NULL,         '2026-02-26 22:00:00', NULL,                  NULL);

-- Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    ('ORD-10001', 'P001', 1, 79.99),
    ('ORD-10001', 'P002', 1, 49.99),
    ('ORD-10002', 'P003', 1, 199.99),
    ('ORD-10003', 'P005', 1, 89.99),
    ('ORD-10004', 'P003', 1, 199.99),
    ('ORD-10004', 'P006', 1, 59.99),
    ('ORD-10005', 'P001', 1, 79.99),
    ('ORD-10006', 'P007', 1, 149.99),
    ('ORD-10006', 'P009', 1, 69.99),
    ('ORD-10007', 'P007', 1, 149.99);
