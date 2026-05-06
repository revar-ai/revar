/* SPDX-License-Identifier: Apache-2.0 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { z } from "zod";
import {
  useAddresses,
  useCart,
  useCheckoutConfirm,
  useCheckoutCoupon,
  useCheckoutReview,
  useCheckoutShipping,
  useCheckoutStart,
  useMe,
} from "../api/hooks";
import { formatPrice } from "../lib/format";

const STEPS = [
  { path: "shipping", label: "Shipping" },
  { path: "review", label: "Review" },
  { path: "confirm", label: "Payment" },
] as const;

function Stepper() {
  const loc = useLocation();
  const current = STEPS.findIndex((s) => loc.pathname.endsWith(`/checkout/${s.path}`));
  return (
    <ol className="flex items-center gap-2 text-sm mb-6" aria-label="Checkout progress">
      {STEPS.map((s, i) => (
        <li
          key={s.path}
          className={`flex items-center gap-2 ${
            i === current ? "font-semibold text-brand-700" : "text-slate-500"
          }`}
          aria-current={i === current ? "step" : undefined}
        >
          <span
            className={`w-6 h-6 rounded-full flex items-center justify-center border ${
              i <= current
                ? "bg-brand-600 text-white border-brand-600"
                : "border-slate-300"
            }`}
          >
            {i + 1}
          </span>
          {s.label}
          {i < STEPS.length - 1 && <span aria-hidden>→</span>}
        </li>
      ))}
    </ol>
  );
}

export function CheckoutPage() {
  const me = useMe();
  const cart = useCart();
  const start = useCheckoutStart();

  // Auto-create the draft order when entering checkout
  useEffect(() => {
    if (me.data?.authenticated && cart.data && cart.data.items.length > 0) {
      start.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me.data?.authenticated, cart.data?.items.length]);

  if (me.isLoading || cart.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!me.data?.authenticated) {
    return (
      <div className="card p-6">
        <h1 className="text-xl font-bold">Sign in to checkout</h1>
        <p className="text-slate-600 mt-2">
          You need an account to complete checkout.
        </p>
        <div className="mt-4 flex gap-3">
          <Link to="/login?redirect=/checkout" className="btn btn-primary">
            Sign in
          </Link>
          <Link to="/signup?redirect=/checkout" className="btn btn-secondary">
            Create account
          </Link>
        </div>
      </div>
    );
  }
  if (!cart.data?.items.length) {
    return (
      <div className="card p-6 text-center">
        <p className="text-slate-500 mb-3">Your cart is empty.</p>
        <Link to="/products" className="btn btn-primary">
          Continue shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Checkout</h1>
      <Stepper />
      <Routes>
        <Route index element={<Navigate to="shipping" replace />} />
        <Route path="shipping" element={<ShippingStep />} />
        <Route path="review" element={<ReviewStep />} />
        <Route path="confirm" element={<ConfirmStep />} />
        <Route path="confirmation/:id" element={<ConfirmationPage />} />
      </Routes>
    </div>
  );
}

function ShippingStep() {
  const addresses = useAddresses();
  const setShipping = useCheckoutShipping();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!addresses.data) return;
    const def = addresses.data.find((a) => a.is_default) ?? addresses.data[0];
    if (def) setSelected(def.id);
  }, [addresses.data]);

  const onContinue = async () => {
    if (selected == null) return;
    try {
      await setShipping.mutateAsync({ address_id: selected });
      navigate("/checkout/review");
    } catch {
      toast.error("Could not save shipping address");
    }
  };

  return (
    <section aria-labelledby="shipping-heading" className="space-y-4">
      <h2 id="shipping-heading" className="text-lg font-semibold">
        Shipping address
      </h2>
      {addresses.isLoading && <p className="text-slate-500">Loading addresses…</p>}
      <ul className="space-y-2" role="radiogroup" aria-label="Saved addresses">
        {addresses.data?.map((a) => (
          <li key={a.id} className="card p-4">
            <label className="flex gap-3 cursor-pointer">
              <input
                type="radio"
                name="shipping-address"
                checked={selected === a.id}
                onChange={() => setSelected(a.id)}
                aria-label={`${a.label} address: ${a.line1}, ${a.city}`}
              />
              <span>
                <strong className="capitalize">{a.label}</strong>
                <span className="block text-sm text-slate-500">
                  {a.full_name} · {a.line1}
                  {a.line2 ? `, ${a.line2}` : ""}, {a.city}, {a.state} {a.postal_code}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="flex justify-between">
        <Link to="/cart" className="btn btn-secondary">
          Back to cart
        </Link>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onContinue}
          disabled={selected == null}
          aria-label="Save and continue to review"
        >
          Save and continue
        </button>
      </div>
    </section>
  );
}

function ReviewStep() {
  const review = useCheckoutReview();
  const couponMut = useCheckoutCoupon();
  const [code, setCode] = useState("");
  const navigate = useNavigate();

  if (review.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (review.isError || !review.data) {
    return <p className="text-rose-600">Could not load review. Please go back to shipping.</p>;
  }

  const r = review.data;
  const onApply = async () => {
    if (!code.trim()) return;
    try {
      const result = await couponMut.mutateAsync(code.trim());
      toast.success(
        `Coupon ${result.coupon} applied — saved ${formatPrice(result.discount_cents)}`,
      );
      review.refetch();
    } catch (err: any) {
      toast.error("Coupon invalid or expired");
    }
  };

  return (
    <section aria-labelledby="review-heading" className="space-y-4">
      <h2 id="review-heading" className="text-lg font-semibold">
        Review your order
      </h2>

      {r.out_of_stock_items.length > 0 && (
        <div role="alert" className="card p-4 bg-rose-50 border-rose-200 text-rose-800">
          <p className="font-medium">Some items in your cart are out of stock:</p>
          <ul className="list-disc pl-5 text-sm mt-1">
            {r.out_of_stock_items.map((i) => (
              <li key={i.product_id}>{i.name}</li>
            ))}
          </ul>
          <p className="text-sm mt-2">
            Reduce the quantity in your cart or remove these items to continue.
          </p>
        </div>
      )}

      <div className="card p-4 space-y-3">
        <h3 className="font-semibold">Items</h3>
        <ul className="divide-y divide-slate-200">
          {r.items.map((it) => (
            <li key={it.product_id} className="py-2 flex justify-between text-sm">
              <span>
                {it.name} × {it.quantity}
              </span>
              <span>{formatPrice(it.line_total_cents)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-4">
        <h3 className="font-semibold mb-2">Promo code</h3>
        <p className="text-xs text-slate-500 mb-2">
          This is the only place where promo codes apply to your order total.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Promo code"
            aria-label="Promo code (checkout)"
            className="input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onApply}
            aria-label="Apply checkout promo code"
          >
            Apply
          </button>
        </div>
        {r.coupon_code && (
          <p className="text-sm text-emerald-700 mt-2">
            Applied: <strong>{r.coupon_code}</strong> (−{formatPrice(r.discount_cents)})
          </p>
        )}
      </div>

      <div className="card p-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span>Subtotal</span>
          <span>{formatPrice(r.subtotal_cents)}</span>
        </div>
        {r.discount_cents > 0 && (
          <div className="flex justify-between text-sm text-emerald-700">
            <span>Discount</span>
            <span>−{formatPrice(r.discount_cents)}</span>
          </div>
        )}
        <div className="flex justify-between font-semibold">
          <span>Total</span>
          <span>{formatPrice(r.total_cents)}</span>
        </div>
      </div>

      <div className="flex justify-between">
        <Link to="/checkout/shipping" className="btn btn-secondary">
          Back
        </Link>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => navigate("/checkout/confirm")}
          disabled={r.out_of_stock_items.length > 0}
          aria-label="Continue to payment"
        >
          Continue to payment
        </button>
      </div>
    </section>
  );
}

const cardSchema = z.object({
  card_number: z
    .string()
    .min(12, "Card number must be at least 12 digits")
    .max(24)
    .regex(/^[0-9 -]+$/, "Only digits, spaces, and hyphens are allowed"),
  card_exp: z.string().regex(/^\d{2}\/\d{2,4}$/, "Use MM/YY or MM/YYYY"),
  card_cvc: z.string().regex(/^\d{3,4}$/, "3-4 digits"),
});

function ConfirmStep() {
  const confirm = useCheckoutConfirm();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof cardSchema>>({
    resolver: zodResolver(cardSchema),
    defaultValues: { card_number: "", card_exp: "", card_cvc: "" },
  });

  const onSubmit = async (data: z.infer<typeof cardSchema>) => {
    setServerError(null);
    try {
      const cleaned = {
        card_number: data.card_number.replace(/[\s-]/g, ""),
        card_exp: data.card_exp,
        card_cvc: data.card_cvc,
      };
      const result = await confirm.mutateAsync(cleaned);
      if (result.status === "paid" && result.order_id) {
        navigate(`/checkout/confirmation/${result.order_id}`);
      } else if (result.status === "3ds_required" && result.redirect_url) {
        // Synthetic 3DS step: surface the redirect to the user
        toast("Additional verification required (3DS)");
        setServerError("3DS verification required. Please complete the prompt and retry.");
      } else {
        setServerError("Unexpected payment status. Please try again.");
      }
    } catch (err: any) {
      const detail = err?.detail ?? {};
      if (typeof detail === "object" && detail.error === "card_declined") {
        setServerError("Your card was declined. Try a different card.");
      } else if (typeof detail === "object" && detail.error === "out_of_stock") {
        setServerError(
          `An item went out of stock during checkout: ${detail.product_name}. Update your cart and try again.`,
        );
      } else if (err?.status === 504) {
        setServerError("The payment provider timed out. Please try again.");
      } else {
        setServerError("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" aria-labelledby="payment-heading">
      <h2 id="payment-heading" className="text-lg font-semibold">
        Payment
      </h2>
      {serverError && (
        <p role="alert" className="card p-3 bg-rose-50 border-rose-200 text-rose-800 text-sm">
          {serverError}
        </p>
      )}
      <div>
        <label htmlFor="card_number" className="label">
          Card number
        </label>
        <input
          id="card_number"
          autoComplete="cc-number"
          inputMode="numeric"
          className="input"
          placeholder="4242 4242 4242 4242"
          {...register("card_number")}
        />
        {errors.card_number && (
          <p className="text-xs text-rose-600 mt-1">{errors.card_number.message}</p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="card_exp" className="label">
            Expiry
          </label>
          <input
            id="card_exp"
            autoComplete="cc-exp"
            placeholder="MM/YY"
            className="input"
            {...register("card_exp")}
          />
          {errors.card_exp && (
            <p className="text-xs text-rose-600 mt-1">{errors.card_exp.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="card_cvc" className="label">
            CVC
          </label>
          <input
            id="card_cvc"
            autoComplete="cc-csc"
            inputMode="numeric"
            className="input"
            {...register("card_cvc")}
          />
          {errors.card_cvc && (
            <p className="text-xs text-rose-600 mt-1">{errors.card_cvc.message}</p>
          )}
        </div>
      </div>

      <div className="flex justify-between">
        <Link to="/checkout/review" className="btn btn-secondary">
          Back
        </Link>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isSubmitting}
          aria-label="Place order"
        >
          {isSubmitting ? "Processing…" : "Place order"}
        </button>
      </div>
    </form>
  );
}

function ConfirmationPage() {
  const loc = useLocation();
  const id = loc.pathname.split("/").pop();
  return (
    <section className="card p-8 text-center space-y-4" aria-labelledby="conf-heading">
      <h2 id="conf-heading" className="text-2xl font-bold text-emerald-700">
        Order confirmed
      </h2>
      <p className="text-slate-600">Thank you. Your order has been placed.</p>
      <p className="text-sm text-slate-500">
        Order #<strong data-testid="order-id">{id}</strong>
      </p>
      <Link to="/account/orders" className="btn btn-primary inline-block">
        View my orders
      </Link>
    </section>
  );
}
