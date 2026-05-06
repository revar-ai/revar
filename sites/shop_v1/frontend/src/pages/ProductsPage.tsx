/* SPDX-License-Identifier: Apache-2.0 */
import { useSearchParams } from "react-router-dom";
import { useCategories, useProducts } from "../api/hooks";
import { Pagination } from "../components/Pagination";
import { ProductCard } from "../components/ProductCard";

export function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const filters = {
    category: params.get("category") ?? undefined,
    q: params.get("q") ?? undefined,
    min_price: params.get("min_price") ? Number(params.get("min_price")) : undefined,
    max_price: params.get("max_price") ? Number(params.get("max_price")) : undefined,
    in_stock: params.get("in_stock") === "1" ? true : undefined,
    sort: params.get("sort") ?? "name",
    page: params.get("page") ? Number(params.get("page")) : 1,
  };
  const cats = useCategories();
  const products = useProducts(filters);

  const update = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(params);
    if (value === undefined || value === "") next.delete(key);
    else next.set(key, value);
    next.delete("page");
    setParams(next);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-[220px,1fr] gap-8">
      <aside className="space-y-6" aria-label="Filters">
        <div>
          <h3 className="font-semibold mb-2">Categories</h3>
          <ul className="space-y-1 text-sm">
            <li>
              <button
                type="button"
                className={`hover:underline ${!filters.category ? "font-semibold" : ""}`}
                onClick={() => update("category", undefined)}
              >
                All
              </button>
            </li>
            {cats.data?.map((c) => (
              <li key={c.slug}>
                <button
                  type="button"
                  className={`hover:underline ${filters.category === c.slug ? "font-semibold" : ""}`}
                  onClick={() => update("category", c.slug)}
                >
                  {c.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="font-semibold mb-2">Price</h3>
          <div className="flex gap-2 text-sm">
            <input
              type="number"
              placeholder="Min ¢"
              aria-label="Minimum price (cents)"
              defaultValue={filters.min_price ?? ""}
              className="input"
              onBlur={(e) => update("min_price", e.target.value)}
            />
            <input
              type="number"
              placeholder="Max ¢"
              aria-label="Maximum price (cents)"
              defaultValue={filters.max_price ?? ""}
              className="input"
              onBlur={(e) => update("max_price", e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={filters.in_stock === true}
              onChange={(e) => update("in_stock", e.target.checked ? "1" : undefined)}
            />
            In stock only
          </label>
        </div>
        <div>
          <label htmlFor="sort" className="font-semibold mb-1 block">
            Sort
          </label>
          <select
            id="sort"
            className="input"
            value={filters.sort}
            onChange={(e) => update("sort", e.target.value)}
          >
            <option value="name">Name (A→Z)</option>
            <option value="price_asc">Price (low to high)</option>
            <option value="price_desc">Price (high to low)</option>
            <option value="rating">Rating</option>
          </select>
        </div>
      </aside>

      <section>
        <header className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">
            {filters.category
              ? cats.data?.find((c) => c.slug === filters.category)?.name ?? "Products"
              : "All products"}
          </h1>
          {products.data && (
            <p className="text-sm text-slate-500">{products.data.total} results</p>
          )}
        </header>

        {products.isLoading && <p className="text-slate-500">Loading…</p>}
        {products.isError && <p className="text-rose-600">Failed to load products.</p>}

        {products.data && products.data.items.length === 0 && (
          <p className="text-slate-500">No products match these filters.</p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.data?.items.map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>

        {products.data && (
          <Pagination page={products.data.page} totalPages={products.data.total_pages} />
        )}
      </section>
    </div>
  );
}
