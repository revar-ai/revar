/* SPDX-License-Identifier: Apache-2.0 */
import { Dialog, Transition } from "@headlessui/react";
import { Fragment, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAddToCart, useProduct } from "../api/hooks";
import { formatPrice } from "../lib/format";

export function ProductDetailPage() {
  const { slug = "" } = useParams();
  const product = useProduct(slug);
  const addToCart = useAddToCart();
  const navigate = useNavigate();
  const [sizeGuideOpen, setSizeGuideOpen] = useState(false);
  const [quantity, setQuantity] = useState(1);

  if (product.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (product.isError || !product.data) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-4">Product not found</h1>
        <Link to="/products" className="btn btn-secondary">
          Back to products
        </Link>
      </div>
    );
  }

  const p = product.data;
  const onAdd = async () => {
    await addToCart.mutateAsync(
      { product_id: p.id, quantity },
      {
        onSuccess: () => toast.success("Added to cart"),
        onError: () => toast.error("Could not add to cart"),
      },
    );
  };

  const onBuyNow = async () => {
    /*
     * AMBIGUOUS UI: "Buy now" looks like "Add to cart" but skips the cart and
     * goes straight to checkout. Agents that confirm via UI feedback need to
     * read button labels (and aria-labels) carefully.
     */
    try {
      await addToCart.mutateAsync({ product_id: p.id, quantity });
      navigate("/checkout");
    } catch {
      toast.error("Could not start checkout");
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
      <div>
        <div className="aspect-square bg-slate-100 rounded-lg flex items-center justify-center text-slate-400">
          {p.name}
        </div>
      </div>
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          {p.category?.name && (
            <Link
              to={`/products?category=${p.category.slug}`}
              className="hover:underline"
            >
              {p.category.name}
            </Link>
          )}
        </p>
        <h1 className="text-3xl font-bold">{p.name}</h1>
        <p className="text-slate-600">{p.short_description}</p>

        <p className="text-2xl font-semibold">{formatPrice(p.price_cents, p.currency)}</p>
        <p className="text-sm text-slate-500" aria-label={`Rated ${p.rating} of 5`}>
          {p.rating.toFixed(1)} ★ ({p.rating_count} reviews)
        </p>

        {p.stock === 0 ? (
          <p className="text-rose-600 font-medium">Out of stock</p>
        ) : p.stock <= 5 ? (
          <p className="text-amber-600 font-medium">Only {p.stock} left in stock</p>
        ) : (
          <p className="text-emerald-600 font-medium">In stock</p>
        )}

        <div className="flex items-center gap-2">
          <label htmlFor="qty" className="label mb-0">
            Quantity
          </label>
          <input
            id="qty"
            type="number"
            min={1}
            max={Math.max(1, p.stock)}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            className="input w-24"
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            className="btn btn-primary"
            onClick={onAdd}
            disabled={p.stock === 0}
            aria-label="Add to cart"
          >
            Add to cart
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onBuyNow}
            disabled={p.stock === 0}
            aria-label="Buy now (skip cart and go to checkout)"
            data-action="buy-now"
          >
            Buy now
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setSizeGuideOpen(true)}
            aria-haspopup="dialog"
          >
            Size guide
          </button>
          {p.stock === 0 && (
            <button type="button" className="btn btn-secondary" aria-label="Notify me when in stock">
              Notify me
            </button>
          )}
        </div>

        <details className="mt-8">
          <summary className="cursor-pointer font-medium">Description</summary>
          <p className="mt-2 text-slate-600 whitespace-pre-line">{p.description}</p>
        </details>
      </div>

      <Transition show={sizeGuideOpen} as={Fragment}>
        <Dialog onClose={() => setSizeGuideOpen(false)} className="relative z-30">
          <div className="fixed inset-0 bg-black/40" aria-hidden />
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Dialog.Panel className="card w-full max-w-md p-6">
              <Dialog.Title className="font-semibold text-lg">Size guide</Dialog.Title>
              <p className="mt-2 text-sm text-slate-600">
                Sizing varies by category. For audio and electronics, sizes refer to driver
                diameter. For apparel, refer to the chart on each product page.
              </p>
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setSizeGuideOpen(false)}
                >
                  Got it
                </button>
              </div>
            </Dialog.Panel>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
}
