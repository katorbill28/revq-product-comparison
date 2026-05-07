PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS platforms (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  brand TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  product_family TEXT NOT NULL,
  flavor TEXT,
  pack_count INTEGER NOT NULL DEFAULT 1,
  unit_quantity INTEGER,
  unit_name TEXT,
  total_quantity INTEGER,
  identity_confidence TEXT NOT NULL CHECK (identity_confidence IN ('exact', 'heuristic', 'manual')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_aliases (
  id INTEGER PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  source TEXT NOT NULL,
  UNIQUE (product_id, alias, source)
);

CREATE TABLE IF NOT EXISTS platform_listings (
  id INTEGER PRIMARY KEY,
  platform_id INTEGER NOT NULL REFERENCES platforms(id),
  product_id TEXT NOT NULL REFERENCES products(id),
  platform_product_id TEXT NOT NULL,
  platform_name TEXT NOT NULL,
  category_path TEXT,
  image_url TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  UNIQUE (platform_id, platform_product_id)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY,
  platform_id INTEGER NOT NULL REFERENCES platforms(id),
  source_file TEXT NOT NULL,
  scraped_at TEXT NOT NULL,
  ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (platform_id, source_file, scraped_at)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
  id INTEGER PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES platform_listings(id) ON DELETE CASCADE,
  scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs(id) ON DELETE CASCADE,
  scraped_at TEXT NOT NULL,
  mrp_cents INTEGER NOT NULL,
  selling_price_cents INTEGER NOT NULL,
  discount_percent REAL NOT NULL,
  currency TEXT NOT NULL DEFAULT 'INR',
  UNIQUE (listing_id, scraped_at)
);

CREATE TABLE IF NOT EXISTS availability_snapshots (
  id INTEGER PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES platform_listings(id) ON DELETE CASCADE,
  scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs(id) ON DELETE CASCADE,
  scraped_at TEXT NOT NULL,
  pincode TEXT NOT NULL,
  in_stock INTEGER NOT NULL CHECK (in_stock IN (0, 1)),
  available_quantity INTEGER,
  UNIQUE (listing_id, scraped_at, pincode)
);

CREATE INDEX IF NOT EXISTS idx_platform_listings_product_platform
  ON platform_listings (product_id, platform_id);

CREATE INDEX IF NOT EXISTS idx_price_history_listing_time
  ON price_snapshots (listing_id, scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_availability_out_of_stock
  ON availability_snapshots (listing_id, pincode, scraped_at DESC)
  WHERE in_stock = 0;

CREATE INDEX IF NOT EXISTS idx_products_identity
  ON products (brand, product_family, flavor, pack_count, total_quantity);
