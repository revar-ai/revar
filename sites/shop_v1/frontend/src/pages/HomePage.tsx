/* SPDX-License-Identifier: Apache-2.0 */
import { Link } from "react-router-dom";
import { useCategories, useProducts } from "../api/hooks";
import { ProductCard } from "../components/ProductCard";

export function HomePage() {
  const cats = useCategories();
  const featured = useProducts({ sort: "rating", page: 1 });

  return (
    <div className="space-y-12">
      <section className="bg-brand-50 rounded-lg p-8 md:p-12">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
          Welcome to Acme Shop
        </h1>
        <p className="mt-3 text-slate-600 max-w-xl">
          Audio, wearables, fragrance and more — handpicked for revar evaluations.
        </p>
        <Link to="/products" className="btn btn-primary mt-6">
          Shop all products
        </Link>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Browse by category</h2>
        <ul className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {cats.data?.map((c) => (
            <li key={c.slug}>
              <Link
                to={`/products?category=${c.slug}`}
                className="card p-4 block text-center hover:shadow-md"
              >
                <span className="font-medium">{c.name}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Top rated</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {featured.data?.items.slice(0, 8).map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>
      </section>
    </div>
  );
}
