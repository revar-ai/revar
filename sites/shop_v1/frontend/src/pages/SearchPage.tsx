/* SPDX-License-Identifier: Apache-2.0 */
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useProductSearch } from "../api/hooks";
import { ProductCard } from "../components/ProductCard";

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const initialQ = params.get("q") ?? "";
  const [q, setQ] = useState(initialQ);
  const debouncedQ = useDebounced(q, 250);
  const search = useProductSearch(debouncedQ);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Sync URL with debounced query so reloading keeps state
  useEffect(() => {
    const next = new URLSearchParams(params);
    if (debouncedQ) next.set("q", debouncedQ);
    else next.delete("q");
    setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  // IntersectionObserver-driven infinite scroll
  useEffect(() => {
    if (!search.hasNextPage || !sentinelRef.current) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) search.fetchNextPage();
        }
      },
      { rootMargin: "200px" },
    );
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [search.hasNextPage, search.fetchNextPage, search]);

  const allItems = search.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <h1 className="text-2xl font-bold">Search</h1>
        <input
          type="search"
          aria-label="Search products"
          className="input max-w-lg"
          placeholder="Search products by name or tag"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
        />
      </header>

      {q.trim().length === 0 && (
        <p className="text-slate-500">Type to start searching.</p>
      )}

      {q.trim().length > 0 && search.isLoading && <p className="text-slate-500">Searching…</p>}

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="search-results"
      >
        {allItems.map((p) => (
          <ProductCard key={p.id} p={p} />
        ))}
      </div>

      {q.trim().length > 0 && allItems.length === 0 && !search.isLoading && (
        <p className="text-slate-500">No results.</p>
      )}

      <div ref={sentinelRef} aria-hidden className="h-8" />
      {search.isFetchingNextPage && (
        <p className="text-center text-slate-500">Loading more…</p>
      )}
    </div>
  );
}
