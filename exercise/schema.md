# Schema Notes

## Cross-platform product identity

I model a product as the canonical item a brand manager thinks about, then attach each marketplace SKU to it through `platform_listings`. A listing keeps the platform's native ID and raw name; `products` keeps the normalized identity: brand, product family, flavor, pack count, unit quantity, and total quantity. The ingestion script turns names like `60 g`, `60GM`, `Pack of 6`, and `6x60g` into the same identity key and stores the original names in `product_aliases`.

This breaks when the title omits an important variant, when marketplaces use different commercial bundles for the same total weight, or when names are close but semantically different. For example, "Almond Crunch" versus "Almond + Cashew Crunch" should not be auto-merged without a human rule, even though the price and weight look similar.

## Index or denormalization for scale

`idx_price_history_listing_time` supports the 30-day history query without scanning all snapshots. For the product page, I would also maintain a small `latest_listing_metrics` table with one row per listing containing latest price, latest scrape time, live pincode count, and total pincode count. That denormalization keeps the page fast while the append-only snapshot tables remain the source of truth.

## At 100x scrape volume

I would partition time-series tables by scrape date, make ingestion idempotent through run-level checksums, and move raw payloads to object storage with a pointer in `platform_listings` or `scrape_runs`. I would also separate canonical identity resolution into its own reviewed workflow so high-volume scrapes can land quickly while uncertain matches are queued for manual approval.
