-- SmartShelf Supabase Setup
-- Dieses SQL im Supabase SQL Editor ausführen (einmalig)

-- Tabelle 1: Produktstammdaten
CREATE TABLE IF NOT EXISTS products (
  prod_id        TEXT PRIMARY KEY,
  prod_name      TEXT NOT NULL,
  supplier_email TEXT NOT NULL,
  supplier_name  TEXT,
  min_qty        INTEGER NOT NULL,
  reorder_qty    INTEGER NOT NULL,
  unit           TEXT DEFAULT 'Stk'
);

-- Tabelle 2: Bestellstatus
CREATE TABLE IF NOT EXISTS orders (
  prod_id     TEXT PRIMARY KEY,
  status      TEXT DEFAULT 'PENDING',
  ordered_at  TIMESTAMPTZ DEFAULT NOW(),
  quantity    INTEGER
);

-- Tabelle 3: Scan-Verlauf
CREATE TABLE IF NOT EXISTS scan_log (
  id          SERIAL PRIMARY KEY,
  shelf_id    TEXT,
  prod_id     TEXT,
  count       INTEGER,
  scanned_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security aktivieren
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_log ENABLE ROW LEVEL SECURITY;

-- HINWEIS: Diese Policies erlauben vollen Zugriff für alle Rollen (inkl. anon).
-- Für den Hackathon akzeptabel, da nur der Server (mit service_role Key) zugreift.
-- Für Produktion müssen restriktive Policies gesetzt werden (siehe README Kapitel 8).
--
-- Produktions-Empfehlung:
--   1. anon-Key im Frontend verwenden (read-only auf products)
--   2. service_role-Key nur serverseitig
--   3. Policies pro Rolle: anon = SELECT, service_role = ALL
CREATE POLICY "Allow all for service_role" ON products FOR ALL USING (true);
CREATE POLICY "Allow all for service_role" ON orders FOR ALL USING (true);
CREATE POLICY "Allow all for service_role" ON scan_log FOR ALL USING (true);

-- SAP-spezifische Spalten hinzufügen (Migration)
ALTER TABLE products ADD COLUMN IF NOT EXISTS sap_stock INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sap_ordered_from_vendors INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sap_ordered_by_customers INTEGER DEFAULT 0;

-- Testdaten (werden durch SAP-Import ersetzt)
INSERT INTO products (prod_id, prod_name, supplier_email, supplier_name, min_qty, reorder_qty, unit) VALUES
  ('PROD-001', 'Wasserflaschen 0.5L', 'lieferant@example.com', 'Getränke AG', 5, 20, 'Stk'),
  ('PROD-002', 'Kartonboxen gross', 'lieferant@example.com', 'Verpackung GmbH', 3, 10, 'Stk'),
  ('PROD-003', 'Kaffeebecher', 'lieferant@example.com', 'Bürobedarf CH', 10, 50, 'Stk')
ON CONFLICT (prod_id) DO NOTHING;
