import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema.sql"
DEFAULT_DB = ROOT / "revq.sqlite"
DEFAULT_APP_JSON = ROOT / "app" / "public" / "products.json"

PLATFORMS = {
    "blinkit": "Blinkit",
    "zepto": "Zepto",
    "instamart": "Swiggy Instamart",
}

TOKEN_REPLACEMENTS = {
    "choc": "chocolate",
    "gm": "g",
    "multigrain": "multi grain",
    "proteinbar": "protein bar",
    "dcrc": "dark chocolate cranberry",
}


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-+", "-", value)


def normalize_text(value):
    text = value.lower().replace("&", " and ").replace("+", " and ")
    for source, target in TOKEN_REPLACEMENTS.items():
        text = re.sub(rf"\b{source}\b", target, text)
    text = re.sub(r"(\d+)\s*gm\b", r"\1 g", text)
    text = re.sub(r"(\d+)\s*x\s*(\d+)\s*g\b", r"\1 x \2 g", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_snapshot_time(raw):
    if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.isdigit()):
        return datetime.fromtimestamp(int(raw), timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(raw, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return f"{raw}T00:00:00Z"
    return raw


def detect_pack_count(text):
    patterns = [
        r"pack\s+of\s+(\d+)",
        r"(\d+)\s*bars?\s+mixed",
        r"(\d+)\s*x\s*\d+\s*g",
        r"\d+\s*g\s*x\s*(\d+)",
        r"(\d+)x\d+\s*g",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return 1


def detect_quantities(text, explicit_weight=None, explicit_unit=None):
    normalized = normalize_text(text)
    pack_count = detect_pack_count(normalized)

    unit_quantity = None
    unit_name = explicit_unit or None
    if explicit_weight:
        unit_quantity = int(float(explicit_weight) * 1000) if explicit_unit == "kg" else int(float(explicit_weight))
        unit_name = "g" if explicit_unit == "kg" else explicit_unit

    pack_match = re.search(r"(\d+)\s*x\s*(\d+)\s*g", normalized)
    if pack_match:
        pack_count = int(pack_match.group(1))
        unit_quantity = int(pack_match.group(2))
        unit_name = "g"

    reverse_pack_match = re.search(r"(\d+)\s*g\s*x\s*(\d+)", normalized)
    if reverse_pack_match:
        unit_quantity = int(reverse_pack_match.group(1))
        pack_count = int(reverse_pack_match.group(2))
        unit_name = "g"

    weights = [int(x) for x in re.findall(r"\b(\d{2,4})\s*g\b", normalized)]
    if weights:
        if unit_quantity is None:
            unit_quantity = weights[0]
        if unit_name is None:
            unit_name = "g"

    kg_match = re.search(r"\b(\d+)\s*kg\b", normalized)
    if kg_match:
        unit_quantity = int(kg_match.group(1)) * 1000
        unit_name = "g"

    total_quantity = None
    if unit_quantity is not None:
        if pack_count > 1 and unit_quantity * pack_count in weights:
            total_quantity = unit_quantity * pack_count
        elif pack_count > 1 and unit_quantity > 120:
            total_quantity = unit_quantity
            unit_quantity = round(unit_quantity / pack_count)
        else:
            total_quantity = unit_quantity * pack_count

    return pack_count, unit_quantity, unit_name or "g", total_quantity


def classify_product(name, price_mrp, explicit_weight=None, explicit_unit=None):
    text = normalize_text(name)
    pack_count, unit_quantity, unit_name, total_quantity = detect_quantities(
        text, explicit_weight, explicit_unit
    )

    family = "unknown"
    flavor = None
    if "energy bar" in text or "multi grain" in text:
        family = "multi grain energy bar"
    elif (
        "protein bar" in text
        or ("protein" in text and "bar" in text)
        or ("bar" in text and any(token in text for token in [
            "chocolate chunk",
            "peanut butter choc",
            "almond fudge",
            "double cocoa",
            "variety",
        ]))
    ):
        family = "protein bar"
    elif "muesli" in text:
        family = "muesli"
    elif "cereal" in text:
        family = "breakfast cereal"
    elif "peanut butter" in text:
        family = "peanut butter"
    elif "oats" in text:
        family = "rolled oats"

    flavor_rules = [
        ("dark chocolate and cranberry", "dark chocolate and cranberry"),
        ("dark chocolate cranberry", "dark chocolate and cranberry"),
        ("chocolate chunk nuts", "chocolate chunk and nuts"),
        ("chocolate chunk and nuts", "chocolate chunk and nuts"),
        ("peanut butter chocolate", "peanut butter chocolate"),
        ("peanut butter choc", "peanut butter chocolate"),
        ("almond fudge", "almond fudge"),
        ("cranberry", "cranberry"),
        ("mango", "mango"),
        ("almond crunch", "almond crunch"),
        ("almond and cashew crunch", "almond and cashew crunch"),
        ("choco almond", "choco almond"),
        ("crunchy", "crunchy"),
        ("smooth", "smooth"),
        ("dark chocolate", "dark chocolate"),
        ("double cocoa", "double cocoa"),
        ("variety", "variety"),
    ]
    for needle, label in flavor_rules:
        if needle in text:
            flavor = label
            break

    if family == "peanut butter" and flavor in {"peanut butter chocolate", None}:
        if "dark chocolate" in text:
            flavor = "dark chocolate"

    if pack_count == 1 and price_mrp and price_mrp >= 500 and family == "protein bar":
        pack_count = 6 if price_mrp < 800 else 12
        if unit_quantity:
            total_quantity = unit_quantity * pack_count

    if family == "protein bar" and pack_count > 1 and total_quantity is None:
        unit_quantity = 60
        unit_name = "g"
        total_quantity = unit_quantity * pack_count

    bits = ["yogabar", family, flavor or "plain", f"pack-{pack_count}"]
    if total_quantity:
        bits.append(f"{total_quantity}{unit_name}")
    product_id = slugify("-".join(bits))

    canonical_name = "Yogabar " + " ".join(
        part.title() for part in [flavor, family] if part and part != "plain"
    )
    if pack_count > 1:
        canonical_name += f" - Pack of {pack_count}"
    if total_quantity:
        canonical_name += f" ({total_quantity} {unit_name})"

    return {
        "id": product_id,
        "brand": "Yogabar",
        "canonical_name": canonical_name,
        "product_family": family,
        "flavor": flavor,
        "pack_count": pack_count,
        "unit_quantity": unit_quantity,
        "unit_name": unit_name,
        "total_quantity": total_quantity,
        "identity_confidence": "heuristic",
    }


def normalize_payload(path):
    payload = json.loads(path.read_text(encoding="utf-8"))

    if "products" in payload:
        platform = payload["platform"]
        scraped_at = parse_snapshot_time(payload["scraped_at"])
        brand = payload.get("brand", "Yogabar")
        for item in payload["products"]:
            yield {
                "platform": platform,
                "display_platform": PLATFORMS[platform],
                "scraped_at": scraped_at,
                "brand": brand,
                "platform_product_id": item["blinkit_id"],
                "platform_name": item["name"],
                "category_path": item.get("category"),
                "mrp": item["mrp"],
                "selling_price": item["selling_price"],
                "discount_percent": item.get("discount_percent"),
                "image_url": item.get("image_url"),
                "availability": [
                    {
                        "pincode": row["pincode"],
                        "in_stock": bool(row["in_stock"]),
                        "quantity": None,
                    }
                    for row in item.get("availability", [])
                ],
                "raw": item,
                "weight": None,
                "weight_unit": None,
            }
    elif "results" in payload:
        platform = "instamart"
        scraped_at = parse_snapshot_time(payload["snapshot_time"])
        for item in payload["results"]:
            mrp = item["store_mrp"]
            price = item["store_selling_price"]
            yield {
                "platform": platform,
                "display_platform": payload["platform_name"],
                "scraped_at": scraped_at,
                "brand": "Yogabar",
                "platform_product_id": item["product_id"],
                "platform_name": item["display_name"],
                "category_path": None,
                "mrp": mrp,
                "selling_price": price,
                "discount_percent": round((mrp - price) * 100 / mrp, 2) if mrp else 0,
                "image_url": item.get("image"),
                "availability": [
                    {
                        "pincode": row["pin"],
                        "in_stock": int(row.get("available_qty", 0)) > 0,
                        "quantity": row.get("available_qty"),
                    }
                    for row in item.get("store_availability", [])
                ],
                "raw": item,
                "weight": item.get("weight"),
                "weight_unit": item.get("weight_unit"),
            }
    elif "items" in payload:
        platform = "zepto"
        scraped_at = parse_snapshot_time(payload["fetched_on"])
        for item in payload["items"]:
            mrp = item["price"]["mrp"]
            price = item["price"]["final"]
            yield {
                "platform": platform,
                "display_platform": PLATFORMS[platform],
                "scraped_at": scraped_at,
                "brand": "Yogabar",
                "platform_product_id": item["sku_code"],
                "platform_name": item["title"],
                "category_path": " > ".join(item.get("category_path", [])),
                "mrp": mrp,
                "selling_price": price,
                "discount_percent": round((mrp - price) * 100 / mrp, 2) if mrp else 0,
                "image_url": item.get("image"),
                "availability": [
                    {
                        "pincode": pin,
                        "in_stock": status == "available",
                        "quantity": None,
                    }
                    for pin, status in item.get("stock_by_pincode", {}).items()
                ],
                "raw": item,
                "weight": None,
                "weight_unit": None,
            }
    else:
        raise ValueError(f"Unsupported JSON format: {path}")


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def upsert_platform(conn, code, display_name):
    conn.execute(
        "INSERT INTO platforms (code, display_name) VALUES (?, ?) "
        "ON CONFLICT(code) DO UPDATE SET display_name = excluded.display_name",
        (code, display_name),
    )
    return conn.execute("SELECT id FROM platforms WHERE code = ?", (code,)).fetchone()["id"]


def ingest_file(conn, path):
    count = 0
    for row in normalize_payload(path):
        platform_id = upsert_platform(conn, row["platform"], row["display_platform"])
        product = classify_product(
            row["platform_name"], row["mrp"], row["weight"], row["weight_unit"]
        )

        conn.execute(
            """
            INSERT INTO products (
              id, brand, canonical_name, product_family, flavor, pack_count,
              unit_quantity, unit_name, total_quantity, identity_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              canonical_name = excluded.canonical_name,
              product_family = excluded.product_family,
              flavor = excluded.flavor,
              pack_count = excluded.pack_count,
              unit_quantity = excluded.unit_quantity,
              unit_name = excluded.unit_name,
              total_quantity = excluded.total_quantity
            """,
            (
                product["id"],
                product["brand"],
                product["canonical_name"],
                product["product_family"],
                product["flavor"],
                product["pack_count"],
                product["unit_quantity"],
                product["unit_name"],
                product["total_quantity"],
                product["identity_confidence"],
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO product_aliases (product_id, alias, source) VALUES (?, ?, ?)",
            (product["id"], row["platform_name"], row["platform"]),
        )

        conn.execute(
            """
            INSERT INTO scrape_runs (platform_id, source_file, scraped_at)
            VALUES (?, ?, ?)
            ON CONFLICT(platform_id, source_file, scraped_at) DO NOTHING
            """,
            (platform_id, path.name, row["scraped_at"]),
        )
        scrape_run_id = conn.execute(
            """
            SELECT id FROM scrape_runs
            WHERE platform_id = ? AND source_file = ? AND scraped_at = ?
            """,
            (platform_id, path.name, row["scraped_at"]),
        ).fetchone()["id"]

        conn.execute(
            """
            INSERT INTO platform_listings (
              platform_id, product_id, platform_product_id, platform_name,
              category_path, image_url, first_seen_at, last_seen_at, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform_id, platform_product_id) DO UPDATE SET
              product_id = excluded.product_id,
              platform_name = excluded.platform_name,
              category_path = excluded.category_path,
              image_url = excluded.image_url,
              last_seen_at = excluded.last_seen_at,
              raw_payload = excluded.raw_payload
            """,
            (
                platform_id,
                product["id"],
                row["platform_product_id"],
                row["platform_name"],
                row["category_path"],
                row["image_url"],
                row["scraped_at"],
                row["scraped_at"],
                json.dumps(row["raw"], separators=(",", ":")),
            ),
        )
        listing_id = conn.execute(
            "SELECT id FROM platform_listings WHERE platform_id = ? AND platform_product_id = ?",
            (platform_id, row["platform_product_id"]),
        ).fetchone()["id"]

        conn.execute(
            """
            INSERT INTO price_snapshots (
              listing_id, scrape_run_id, scraped_at, mrp_cents,
              selling_price_cents, discount_percent
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(listing_id, scraped_at) DO UPDATE SET
              mrp_cents = excluded.mrp_cents,
              selling_price_cents = excluded.selling_price_cents,
              discount_percent = excluded.discount_percent
            """,
            (
                listing_id,
                scrape_run_id,
                row["scraped_at"],
                int(round(row["mrp"] * 100)),
                int(round(row["selling_price"] * 100)),
                row["discount_percent"],
            ),
        )

        for availability in row["availability"]:
            conn.execute(
                """
                INSERT INTO availability_snapshots (
                  listing_id, scrape_run_id, scraped_at, pincode, in_stock, available_quantity
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(listing_id, scraped_at, pincode) DO UPDATE SET
                  in_stock = excluded.in_stock,
                  available_quantity = excluded.available_quantity
                """,
                (
                    listing_id,
                    scrape_run_id,
                    row["scraped_at"],
                    availability["pincode"],
                    1 if availability["in_stock"] else 0,
                    availability["quantity"],
                ),
            )
        count += 1
    conn.commit()
    return count


def export_app_json(conn, output_path):
    rows = conn.execute(
        """
        WITH latest_price AS (
          SELECT ps.*
          FROM price_snapshots ps
          JOIN (
            SELECT listing_id, MAX(scraped_at) AS scraped_at
            FROM price_snapshots
            GROUP BY listing_id
          ) latest ON latest.listing_id = ps.listing_id AND latest.scraped_at = ps.scraped_at
        ),
        availability AS (
          SELECT
            listing_id,
            scraped_at,
            SUM(CASE WHEN in_stock = 1 THEN 1 ELSE 0 END) AS live_pincodes,
            COUNT(*) AS total_pincodes
          FROM availability_snapshots
          GROUP BY listing_id, scraped_at
        )
        SELECT
          p.id AS product_id,
          p.brand,
          p.canonical_name,
          pl.platform_name,
          pl.image_url,
          pf.code AS platform_code,
          pf.display_name AS platform_display_name,
          lp.mrp_cents,
          lp.selling_price_cents,
          lp.discount_percent,
          lp.scraped_at,
          COALESCE(a.live_pincodes, 0) AS live_pincodes,
          COALESCE(a.total_pincodes, 0) AS total_pincodes
        FROM products p
        JOIN platform_listings pl ON pl.product_id = p.id
        JOIN platforms pf ON pf.id = pl.platform_id
        LEFT JOIN latest_price lp ON lp.listing_id = pl.id
        LEFT JOIN availability a ON a.listing_id = pl.id AND a.scraped_at = lp.scraped_at
        ORDER BY p.canonical_name, pf.display_name
        """
    ).fetchall()

    products = {}
    for row in rows:
        product = products.setdefault(
            row["product_id"],
            {
                "id": row["product_id"],
                "brand": row["brand"],
                "name": row["canonical_name"],
                "image": row["image_url"],
                "platforms": [],
            },
        )
        if not product["image"] and row["image_url"]:
            product["image"] = row["image_url"]
        product["platforms"].append(
            {
                "code": row["platform_code"],
                "name": row["platform_display_name"],
                "listingName": row["platform_name"],
                "currentPrice": row["selling_price_cents"] / 100 if row["selling_price_cents"] else None,
                "mrp": row["mrp_cents"] / 100 if row["mrp_cents"] else None,
                "discountPercent": row["discount_percent"],
                "livePincodes": row["live_pincodes"],
                "totalPincodes": row["total_pincodes"],
                "lastScrapedAt": row["scraped_at"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(list(products.values()), indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Ingest RevQ sample scrape JSON into SQLite.")
    parser.add_argument("files", nargs="*", type=Path, help="Sample JSON file(s) to ingest.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path.")
    parser.add_argument(
        "--export-app-json",
        type=Path,
        default=DEFAULT_APP_JSON,
        help="Write the app's preloaded JSON view.",
    )
    args = parser.parse_args()

    files = args.files or sorted((ROOT / "data").glob("*_sample.json"))
    conn = connect(args.db)
    total = 0
    for path in files:
        total += ingest_file(conn, path.resolve())
    export_app_json(conn, args.export_app_json)
    print(f"Ingested {total} listings into {args.db}")
    print(f"Wrote app data to {args.export_app_json}")


if __name__ == "__main__":
    main()
