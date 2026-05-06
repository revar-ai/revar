/* SPDX-License-Identifier: Apache-2.0 */
import { Link } from "react-router-dom";
import type { Product } from "../api/types";
import { formatPrice } from "../lib/format";

export function ProductCard({ p }: { p: Product }) {
  return (
    <article
      className="card p-4 flex flex-col gap-2 hover:shadow-md transition-shadow"
      data-product-id={p.id}
      data-product-slug={p.slug}
    >
      <div className="aspect-square bg-slate-100 rounded-md flex items-center justify-center text-slate-400 text-xs">
        {/* Image placeholder. Real images would live at /static/products/* */}
        {p.name}
      </div>
      <Link
        to={`/products/${p.slug}`}
        className="font-medium leading-tight text-slate-900 hover:text-brand-700"
      >
        {p.name}
      </Link>
      <p className="text-sm text-slate-500 line-clamp-2">{p.short_description}</p>
      <div className="flex items-center justify-between mt-auto">
        <span className="font-semibold">{formatPrice(p.price_cents, p.currency)}</span>
        <span className="text-xs text-slate-500" aria-label={`Rated ${p.rating} of 5`}>
          {p.rating.toFixed(1)} ★ ({p.rating_count})
        </span>
      </div>
      {p.stock === 0 && (
        <p className="text-xs text-rose-600">Out of stock</p>
      )}
      {p.stock > 0 && p.stock <= 5 && (
        <p className="text-xs text-amber-600">Only {p.stock} left</p>
      )}
    </article>
  );
}
