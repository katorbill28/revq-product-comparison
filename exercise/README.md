# RevQ Take-Home Exercise

**Time:** 4 hours, one sitting. Don't go over.

## Context

RevQ is a brand intelligence platform for D2C brands selling on Indian quick-commerce: Blinkit, Zepto, and Swiggy Instamart. We track availability, pricing, listing position, and share-of-voice across pincodes and cities. Customers are brand managers and growth leads at companies doing ₹5–50 cr/yr on these platforms.

You're going to build a slice of RevQ: schema, ingestion, and a product detail screen. We're hiring for someone who can own pieces of our architecture and ship a clean frontend, so that's what this is calibrated to test.

## What you have

In `/data`:

- `blinkit_sample.json`
- `zepto_sample.json`
- `instamart_sample.json`

Same brand (Yogabar), scraped the same day, ~15–20 products each. Each platform has its own ID format, its own naming conventions, its own unit conventions, its own availability format, and its own price structure. Some products clearly match across platforms. Some don't. Some are only on one platform. A few have ambiguities you'll have to make a judgment call on.

This is what real scrape data looks like.

---

## Part 1 — Schema design (1 hour)

Design a database schema that supports these three queries cleanly:

1. Current price of Product X on all 3 platforms
2. 30-day price history of Product X on Blinkit
3. Pincodes where Product X is out of stock, per platform

The sample data is a single-day snapshot, but your schema must support time-series price and availability — that's the production reality.

**Deliverables:**

- `schema.sql` — tables, columns, types, primary keys, foreign keys, and any indexes you'd add
- `schema.md` — short, answering:
  1. How do you model a "product" that exists across 3 platforms with 3 different IDs and 3 different name strings? What does your approach break on?
  2. One denormalization or one index you'd add for scale, and why
  3. What you'd change if scrape volume went 100×

We weight this part heavily. Schema is where architectural thinking shows up.

## Part 2 — Ingestion (30 minutes)

Write `ingest.py` (or `.js`) that reads any one of the three sample JSONs and writes to your schema. SQLite is fine. One command to run.

We're checking whether you actually applied your Part 1 matching logic, or quietly punted on it.

## Part 3 — React UI (2 hours 30 minutes)

Single-page React app. One route: `/product/:id`. Read from your SQLite via a tiny Express/Flask layer, or pre-load the data — your call.

**Must show:**

- Product name, brand, image
- Price comparison table — row per platform, columns for current price, MRP, discount %
- Availability — "Live in X of Y pincodes" per platform
- Last-scraped timestamp per platform
- Empty, loading, and error states for all of the above

**Don't build:**

- Auth, multi-page routing, navigation chrome
- A design system or animations
- Anything beyond the requirements above

Any CSS approach. Any component library, or none. Your call. We care about component boundaries, prop shapes, where state lives, and how you handle empty/loading/error — not visual flair.

---

## Submission

Send a repo link or zip with this structure:

```
/schema.sql
/schema.md
/ingest        (script + one-command run instructions)
/app           (React app + one-command run instructions)
README.md
```

The submission `README.md` should answer, in this order:

1. **Cross-platform product identity** — how you solved it, what breaks it
2. **Component tree** of your React app, and one paragraph on why you split it that way
3. **Where state lives** in your app and why there
4. **What's fragile or unfinished** — honest list
5. **Next 4 hours** — what you'd build, and why that before anything else

## What we look for

- Schema: did you actually solve cross-platform identity, or punt
- React: clean component boundaries, sensible state placement, real handling of empty/loading/error
- Honesty: a `README.md` that names the cuts and the cracks

## What we don't look for

- A complete product. It doesn't fit in 4 hours. Cut hard.
- A pretty UI on a broken schema.
- A `README.md` that narrates your code. We read code.

---

Reply with the link **within 3 days of receiving this brief**. Include any questions you couldn't get answered while building. We read those carefully.
