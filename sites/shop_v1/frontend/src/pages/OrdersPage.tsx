/* SPDX-License-Identifier: Apache-2.0 */
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { useMe, useOrders } from "../api/hooks";
import { Pagination } from "../components/Pagination";
import { formatPrice } from "../lib/format";

export function OrdersPage() {
  const me = useMe();
  const [params] = useSearchParams();
  const page = params.get("page") ? Number(params.get("page")) : 1;
  const orders = useOrders(page);

  if (me.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!me.data?.authenticated)
    return <Navigate to="/login?redirect=/account/orders" replace />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Your orders</h1>
      {orders.isLoading && <p className="text-slate-500">Loading…</p>}
      {orders.data && orders.data.items.length === 0 && (
        <p className="text-slate-500">You haven't placed any orders yet.</p>
      )}
      <ul className="card divide-y divide-slate-200">
        {orders.data?.items.map((o) => (
          <li key={o.id} className="p-4 flex justify-between items-center" data-order-id={o.id}>
            <div>
              <Link to={`/account/orders/${o.id}`} className="font-medium">
                Order #{o.id}
              </Link>
              <p className="text-sm text-slate-500">
                {o.created_at?.slice(0, 10)} · status {o.status}
              </p>
            </div>
            <span className="font-semibold">{formatPrice(o.total_cents)}</span>
          </li>
        ))}
      </ul>
      {orders.data && (
        <Pagination page={orders.data.page} totalPages={orders.data.total_pages} />
      )}
    </div>
  );
}
