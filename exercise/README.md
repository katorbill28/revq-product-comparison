# RevQ Take-Home Submission

Hey there! Here's my take on the RevQ quick-commerce product tracking exercise. I built out a full system: database schema, data ingestion pipeline, and a React app for viewing product details. Let me walk you through what I did and why.

## The Big Picture

This is a product detail page for quick-commerce platforms (Blinkit, Zepto, Swiggy Instamart). It shows you a product across all platforms with current prices, availability, and when it was last scraped. Behind the scenes, there's a SQLite database that normalizes products from different platforms and tracks price/availability over time.

---

## 1. Figuring Out Product Identity Across Platforms

The tricky part here is that the same product shows up differently on each platform. Blinkit might call it "Yogabar Chocolate Chunk & Nuts Protein Bar (60 g)", while Zepto says "YOGABAR CHOCOLATE CHUNK NUTS PROTEIN BAR 60GM", and Instamart has "Yogabar Protein Bar | Chocolate Chunk & Nuts | 60g | Pack of 1".

My approach: I created a "products" table for the canonical product identity, and separate tables for each platform's listing. The identity key is built from brand, product family, flavor, pack count, unit size, and total weight. I normalize the text (lowercase, remove extra spaces, handle common abbreviations like "choc" → "chocolate"), detect pack counts from patterns like "6x60g", and classify products into categories.

What could break this? If a product title is missing key info (like no flavor mentioned), or if there are true variants that look the same but aren't (I kept "Almond Crunch" separate from "Almond + Cashew Crunch"). Bundles and promos are also tricky. For production, I'd add a manual review system and confidence scores.

---

## 2. React App Structure

I built a single-page app with these components:

- **App**: Handles data fetching and routing
- **ProductPage**: Shows the product details, with platforms sorted by price
- **ProductHeader**: Brand, name, and image (with fallback if the image doesn't load)
- **PriceComparisonTable**: Table of prices with badges for cheapest/best discount
- **AvailabilitySummary**: How many pincodes the product is live in per platform
- **ScrapeTimes**: When each platform was last scraped

I split it this way because each section has its own data needs and loading states. Keeps things clean and testable.

---

## 3. Where I Put the State

- **Data fetching**: In the main App component, using a custom hook. Everything depends on this data being loaded.
- **Sorting platforms**: In ProductPage, computed once when the data loads.
- **Image fallback**: Local to the ProductHeader component.
- **Cheapest price calculation**: In the PriceComparisonTable component.

This keeps the state close to where it's used, and the components are mostly pure functions of their props.

---

## 4. What's Not Perfect Yet

- The product matching is rule-based and works for the samples, but could fail on weird edge cases or typos. Needs manual review in production.
- The app reads from a static JSON file, not a live database. No dynamic queries or updates.
- I didn't build the 30-day price history view, even though the schema supports it.
- Timestamps are inconsistent across the sample data (some epoch, some ISO). The app handles it, but it's a data quality issue.
- No tests written yet. Should add them for the matching logic and React components.
- Some product images don't load from the CDNs in the sample data.

---

## 5. If I Had 4 More Hours

1. **Add a backend API** to query the SQLite database directly. This would enable real-time features and multi-product views.

2. **Build a review interface** for ambiguous product matches. Store manual decisions in the database.

3. **Write tests** for the product normalizer and React components, especially around edge cases.

4. **Clean up the timestamp data** or document how to handle inconsistencies.

That order because the API unlocks everything else, and fixing matching is the biggest risk.

---

## How to Run It

### Prerequisites
- Python 3.10+
- Node.js 18+

### Step 1: Process the Data

Run this from the exercise folder:
```bash
python ingest/ingest.py
```

It reads the three JSON files, normalizes everything, and creates a SQLite database plus a JSON file for the app.

### Step 2: Start the App

```bash
cd app
npm install
npm run dev
```

Go to `http://127.0.0.1:5173/product/yogabar-protein-bar-chocolate-chunk-and-nuts-pack-1-60g` to see a product page.

---

## Files Overview

- `schema.sql` - Database tables and indexes
- `schema.md` - Design decisions and scaling notes
- `ingest/ingest.py` - Data processing script
- `app/src/main.jsx` - React app (all components in one file)
- `app/src/styles.css` - Simple styles
- `data/` - Sample JSON files from each platform

Thanks for the interesting exercise! I enjoyed thinking through the cross-platform identity problem.
