/* SPDX-License-Identifier: Apache-2.0 */
import { useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import {
  useApplyCartCoupon,
  useCart,
  useRemoveCartItem,
  useUpdateCartItem,
} from "../api/hooks";
import { formatPrice } from "../lib/format";

export function CartPage() {
  const cart = useCart();
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const applyCoupon = useApplyCartCoupon();
  const [couponInput, setCouponInput] = useState("");

  const items = cart.data?.items ?? [];
  const subtotal = cart.data?.subtotal_cents ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Your cart</h1>
      {items.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-slate-500 mb-4">Your cart is empty.</p>
          <Link to="/products" className="btn btn-primary">
            Continue shopping
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-[1fr,320px] gap-8">
          <ul className="card divide-y divide-slate-200">
            {items.map((it) => (
              <li key={it.id} className="p-4 flex gap-4" data-product-id={it.product_id}>
                <div className="flex-1">
                  <Link to={`/products/${it.slug}`} className="font-medium">
                    {it.name}
                  </Link>
                  <p className="text-sm text-slate-500">
                    {formatPrice(it.unit_price_cents)} each
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <label htmlFor={`qty-${it.id}`} className="text-xs text-slate-500">
                      Qty
                    </label>
                    <input
                      id={`qty-${it.id}`}
                      type="number"
                      min={1}
                      max={99}
                      defaultValue={it.quantity}
                      className="w-16 input"
                      aria-label={`Quantity for ${it.name}`}
                      onChange={(e) => {
                        const qty = Number(e.target.value);
                        if (qty >= 1) {
                          update.mutate({ item_id: it.id, quantity: qty });
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="text-xs text-rose-600 underline ml-3"
                      onClick={() => remove.mutate(it.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatPrice(it.line_total_cents)}</p>
                </div>
              </li>
            ))}
          </ul>
          <aside className="card p-4 space-y-3 self-start">
            <h2 className="font-semibold">Order summary</h2>
            {/*
              Same cart-side coupon input as the drawer. Same ambiguous behavior:
              shows a "Code applied" toast but does NOT change subtotal here.
            */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!couponInput.trim()) return;
                applyCoupon.mutate(couponInput.trim(), {
                  onSuccess: () =>
                    toast.success(`Code applied: ${couponInput.trim().toUpperCase()}`),
                });
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                placeholder="Promo code"
                aria-label="Promo code (cart)"
                className="input"
                value={couponInput}
                onChange={(e) => setCouponInput(e.target.value)}
              />
              <button type="submit" className="btn btn-secondary">
                Apply
              </button>
            </form>
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{formatPrice(subtotal)}</span>
            </div>
            <Link to="/checkout" className="btn btn-primary w-full">
              Checkout
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}
