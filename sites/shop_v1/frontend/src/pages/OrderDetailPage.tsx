/* SPDX-License-Identifier: Apache-2.0 */
import { useState } from "react";
import toast from "react-hot-toast";
import { Link, Navigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useMe, useOrder } from "../api/hooks";
import { formatPrice } from "../lib/format";

export function OrderDetailPage() {
  const { id = "" } = useParams();
  const orderId = Number(id);
  const me = useMe();
  const order = useOrder(orderId);
  const [reason, setReason] = useState("");
  const [returnRequested, setReturnRequested] = useState(false);

  if (me.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!me.data?.authenticated)
    return <Navigate to={`/login?redirect=/account/orders/${id}`} replace />;
  if (order.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (order.isError || !order.data) {
    return (
      <div>
        <h1 className="text-2xl font-bold">Order not found</h1>
        <Link to="/account/orders" className="btn btn-secondary mt-2">
          Back to orders
        </Link>
      </div>
    );
  }

  const o = order.data;

  const requestReturn = async () => {
    if (!reason.trim()) return;
    try {
      await api(`/api/account/orders/${o.id}/return`, {
        method: "POST",
        body: { reason: reason.trim() },
      });
      setReturnRequested(true);
      toast.success("Return requested");
    } catch {
      toast.error("Could not request return");
    }
  };

  return (
    <div className="space-y-6">
      <Link to="/account/orders" className="text-sm">
        ← Back to orders
      </Link>
      <h1 className="text-2xl font-bold">Order #{o.id}</h1>
      <p className="text-sm text-slate-500">
        Status: <strong>{o.status}</strong>
        {o.payment_attempts > 1 && (
          <span> · {o.payment_attempts} payment attempts</span>
        )}
      </p>

      <div className="card p-4">
        <h2 className="font-semibold mb-2">Items</h2>
        <ul className="divide-y divide-slate-200">
          {o.items.map((it, i) => (
            <li key={i} className="py-2 flex justify-between text-sm">
              <span>
                {it.product_name} × {it.quantity}
              </span>
              <span>{formatPrice(it.unit_price_cents * it.quantity)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-4">
        <div className="flex justify-between text-sm">
          <span>Subtotal</span>
          <span>{formatPrice(o.subtotal_cents)}</span>
        </div>
        {o.discount_cents > 0 && (
          <div className="flex justify-between text-sm text-emerald-700">
            <span>Discount ({o.coupon_code})</span>
            <span>−{formatPrice(o.discount_cents)}</span>
          </div>
        )}
        <div className="flex justify-between font-semibold mt-2">
          <span>Total</span>
          <span>{formatPrice(o.total_cents)}</span>
        </div>
      </div>

      {o.status === "paid" && !returnRequested && (
        <div className="card p-4 space-y-2">
          <h2 className="font-semibold">Request a return</h2>
          <textarea
            className="input"
            rows={3}
            placeholder="Why do you want to return this order?"
            aria-label="Return reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <button type="button" className="btn btn-secondary" onClick={requestReturn}>
            Submit return request
          </button>
        </div>
      )}
      {returnRequested && (
        <p role="status" className="text-emerald-700">
          Return requested. We'll be in touch.
        </p>
      )}
    </div>
  );
}
