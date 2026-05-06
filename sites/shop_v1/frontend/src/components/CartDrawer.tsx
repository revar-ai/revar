/* SPDX-License-Identifier: Apache-2.0 */
import { Dialog, Transition } from "@headlessui/react";
import { Fragment, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import {
  useApplyCartCoupon,
  useCart,
  useRemoveCartItem,
  useUpdateCartItem,
} from "../api/hooks";
import { formatPrice } from "../lib/format";

export function CartDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const cart = useCart();
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const applyCoupon = useApplyCartCoupon();
  const [couponInput, setCouponInput] = useState("");
  const [removing, setRemoving] = useState<number | null>(null);

  const items = cart.data?.items ?? [];
  const subtotal = cart.data?.subtotal_cents ?? 0;

  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-30">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" aria-hidden />
        </Transition.Child>
        <div className="fixed inset-y-0 right-0 max-w-full flex">
          <Transition.Child
            as={Fragment}
            enter="transform transition ease-out duration-200"
            enterFrom="translate-x-full"
            enterTo="translate-x-0"
            leave="transform transition ease-in duration-150"
            leaveFrom="translate-x-0"
            leaveTo="translate-x-full"
          >
            <Dialog.Panel className="w-screen max-w-md bg-white h-full flex flex-col shadow-xl">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <Dialog.Title className="text-lg font-semibold">Your cart</Dialog.Title>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={onClose}
                  aria-label="Close cart"
                >
                  Close
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-4" data-testid="cart-items">
                {items.length === 0 ? (
                  <p className="text-slate-500">Your cart is empty.</p>
                ) : (
                  <ul className="divide-y divide-slate-200">
                    {items.map((it) => (
                      <li key={it.id} className="py-4 flex gap-3" data-product-id={it.product_id}>
                        <div className="flex-1">
                          <Link to={`/products/${it.slug}`} className="font-medium">
                            {it.name}
                          </Link>
                          <p className="text-sm text-slate-500">
                            {formatPrice(it.unit_price_cents)} ×{" "}
                            <input
                              type="number"
                              min={1}
                              max={99}
                              defaultValue={it.quantity}
                              aria-label={`Quantity for ${it.name}`}
                              className="w-16 input inline-block"
                              onChange={(e) => {
                                const qty = Number(e.target.value);
                                if (qty >= 1) {
                                  update.mutate({ item_id: it.id, quantity: qty });
                                }
                              }}
                            />
                          </p>
                          {!it.in_stock && (
                            <p className="text-xs text-rose-600 mt-1">
                              Quantity exceeds available stock.
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <p>{formatPrice(it.line_total_cents)}</p>
                          <button
                            type="button"
                            className="text-xs text-rose-600 underline mt-2"
                            onClick={() => setRemoving(it.id)}
                          >
                            Remove
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="px-6 py-4 border-t border-slate-200 space-y-3">
                {/*
                  Cart-side coupon input.
                  This is the deliberate AMBIGUOUS UI: the toast says "Code applied"
                  but it does NOT affect totals. Only the checkout-side input applies.
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
                  <button type="submit" className="btn btn-secondary" aria-label="Apply promo code">
                    Apply
                  </button>
                </form>

                <div className="flex items-center justify-between text-base font-medium">
                  <span>Subtotal</span>
                  <span>{formatPrice(subtotal)}</span>
                </div>
                <Link
                  to="/checkout"
                  className="btn btn-primary w-full"
                  onClick={onClose}
                  aria-disabled={items.length === 0}
                >
                  Checkout
                </Link>
              </div>

              {/* Remove-item confirmation modal (the second modal pattern) */}
              <Transition show={removing !== null} as={Fragment}>
                <Dialog
                  onClose={() => setRemoving(null)}
                  className="relative z-40"
                >
                  <div className="fixed inset-0 bg-black/40" aria-hidden />
                  <div className="fixed inset-0 flex items-center justify-center p-4">
                    <Dialog.Panel className="card w-full max-w-sm p-6">
                      <Dialog.Title className="font-semibold text-lg">Remove item?</Dialog.Title>
                      <p className="mt-2 text-sm text-slate-600">
                        This will remove the item from your cart. You can add it back later.
                      </p>
                      <div className="mt-4 flex justify-end gap-2">
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => setRemoving(null)}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          onClick={() => {
                            if (removing !== null) {
                              remove.mutate(removing);
                              setRemoving(null);
                            }
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    </Dialog.Panel>
                  </div>
                </Dialog>
              </Transition>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
