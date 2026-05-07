import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AlertCircle, CheckCircle2, Clock3, PackageSearch } from "lucide-react";
import "./styles.css";

const PLATFORM_ORDER = ["blinkit", "zepto", "instamart"];

function currency(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function dateTime(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(parsed);
}

function readProductId() {
  const match = window.location.pathname.match(/^\/product\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

function useProductData() {
  const [state, setState] = useState({ status: "loading", products: [] });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading", products: [] });
      try {
        const response = await fetch("/products.json");
        if (!response.ok) {
          throw new Error(`Data request failed with ${response.status}`);
        }
        const products = await response.json();
        if (!cancelled) {
          setState({ status: "ready", products });
        }
      } catch (error) {
        if (!cancelled) {
          setState({ status: "error", error: error.message, products: [] });
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

function App() {
  const productId = readProductId();
  const data = useProductData();

  if (!productId) {
    return (
      <PageShell>
        <StateBlock
          icon={<PackageSearch size={28} />}
          title="Open a product route"
          message="Use /product/yogabar-protein-bar-chocolate-chunk-and-nuts-pack-1-60g."
        />
      </PageShell>
    );
  }

  if (data.status === "loading") {
    return (
      <PageShell>
        <ProductSkeleton />
      </PageShell>
    );
  }

  if (data.status === "error") {
    return (
      <PageShell>
        <StateBlock
          icon={<AlertCircle size={28} />}
          title="Could not load product data"
          message={data.error}
        />
      </PageShell>
    );
  }

  if (data.status === "ready" && data.products.length === 0) {
    return (
      <PageShell>
        <StateBlock
          icon={<AlertCircle size={28} />}
          title="No products available"
          message="The data source returned no normalized products. Run ingest again or check the JSON export."
        />
      </PageShell>
    );
  }

  const product = data.products.find((item) => item.id === productId);
  if (!product) {
    return (
      <PageShell>
        <StateBlock
          icon={<PackageSearch size={28} />}
          title="Product not found"
          message={`No normalized product exists for "${productId}".`}
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <ProductPage product={product} />
    </PageShell>
  );
}

function PageShell({ children }) {
  return (
    <main className="page">
      <div className="content">{children}</div>
    </main>
  );
}

function ProductPage({ product }) {
  const platforms = useMemo(
    () =>
      [...product.platforms].sort(
        (left, right) =>
          PLATFORM_ORDER.indexOf(left.code) - PLATFORM_ORDER.indexOf(right.code),
      ),
    [product.platforms],
  );

  return (
    <>
      <ProductHeader product={product} />
      <section className="section">
        <SectionHeading title="Price comparison" />
        <PriceComparisonTable platforms={platforms} />
      </section>
      <section className="section">
        <SectionHeading title="Availability" />
        <AvailabilitySummary platforms={platforms} />
      </section>
      <section className="section">
        <SectionHeading title="Last scraped" />
        <ScrapeTimes platforms={platforms} />
      </section>
    </>
  );
}

function ProductHeader({ product }) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = product.image && !imageFailed;

  return (
    <header className="product-header">
      <div className="image-wrap">
        {hasImage ? (
          <img
            src={product.image}
            alt={product.name}
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="image-fallback">
            <PackageSearch size={36} />
            <span>Image unavailable</span>
          </div>
        )}
      </div>
      <div>
        <p className="brand">{product.brand}</p>
        <h1>{product.name}</h1>
        <p className="muted">{product.id}</p>
      </div>
    </header>
  );
}

function SectionHeading({ title }) {
  return <h2>{title}</h2>;
}

function PriceComparisonTable({ platforms }) {
  if (!platforms.length) {
    return <InlineEmpty message="No platform listings are attached to this product." />;
  }

  const cheapestPrice = useMemo(() => {
    const prices = platforms
      .map((platform) => platform.currentPrice)
      .filter((price) => typeof price === "number");
    return prices.length ? Math.min(...prices) : null;
  }, [platforms]);

  const bestDiscount = useMemo(() => {
    const discounts = platforms
      .map((platform) => platform.discountPercent)
      .filter((value) => typeof value === "number");
    return discounts.length ? Math.max(...discounts) : null;
  }, [platforms]);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Platform</th>
            <th>Current price</th>
            <th>MRP</th>
            <th>Discount</th>
          </tr>
        </thead>
        <tbody>
          {platforms.map((platform) => {
            const isCheapest = platform.currentPrice === cheapestPrice;
            const isBestDiscount = platform.discountPercent === bestDiscount && bestDiscount > 0;

            return (
              <tr key={platform.code} className={isCheapest ? "highlight-row" : ""}>
                <td>
                  <strong>{platform.name}</strong>
                  {isCheapest ? <span className="pill pill-cheapest">Cheapest</span> : null}
                  <span>{platform.listingName}</span>
                </td>
                <td>{currency(platform.currentPrice)}</td>
                <td>{currency(platform.mrp)}</td>
                <td>
                  {platform.discountPercent?.toFixed(1) ?? "—"}%
                  {isBestDiscount ? <span className="pill pill-discount">Best discount</span> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AvailabilitySummary({ platforms }) {
  if (!platforms.length) {
    return <InlineEmpty message="No availability snapshots are available." />;
  }

  return (
    <div className="availability-grid">
      {platforms.map((platform) => (
        <article className="availability-item" key={platform.code}>
          <div>
            <strong>{platform.name}</strong>
            <p>Live in {platform.livePincodes} of {platform.totalPincodes} pincodes</p>
          </div>
          <span className={platform.livePincodes > 0 ? "status-live" : "status-empty"}>
            <CheckCircle2 size={18} />
            {platform.livePincodes > 0 ? "Live" : "OOS"}
          </span>
        </article>
      ))}
    </div>
  );
}

function ScrapeTimes({ platforms }) {
  if (!platforms.length) {
    return <InlineEmpty message="No scrape timestamps found." />;
  }

  return (
    <div className="scrape-list">
      {platforms.map((platform) => (
        <div className="scrape-row" key={platform.code}>
          <Clock3 size={18} />
          <strong>{platform.name}</strong>
          <span>{dateTime(platform.lastScrapedAt)}</span>
        </div>
      ))}
    </div>
  );
}

function ProductSkeleton() {
  return (
    <>
      <div className="product-header">
        <div className="skeleton image-wrap" />
        <div className="skeleton-copy">
          <span className="skeleton line short" />
          <span className="skeleton line title" />
          <span className="skeleton line" />
        </div>
      </div>
      <div className="skeleton block" />
      <div className="skeleton block compact" />
    </>
  );
}

function InlineEmpty({ message }) {
  return <p className="inline-empty">{message}</p>;
}

function StateBlock({ icon, title, message }) {
  return (
    <section className="state-block">
      {icon}
      <h1>{title}</h1>
      <p>{message}</p>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
