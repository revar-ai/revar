/* SPDX-License-Identifier: Apache-2.0 */
import { Link, Navigate } from "react-router-dom";
import { useAddresses, useMe } from "../api/hooks";

export function AccountPage() {
  const me = useMe();
  const addresses = useAddresses();

  if (me.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!me.data?.authenticated) return <Navigate to="/login?redirect=/account" replace />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">My account</h1>
        <p className="text-slate-500">Welcome, {me.data.user?.full_name}.</p>
      </header>

      <section className="grid md:grid-cols-2 gap-4">
        <Link to="/account/orders" className="card p-4 hover:shadow-md">
          <h2 className="font-semibold">Orders</h2>
          <p className="text-sm text-slate-500">View past orders and request returns.</p>
        </Link>
        <div className="card p-4">
          <h2 className="font-semibold">Addresses</h2>
          <ul className="mt-2 space-y-2 text-sm">
            {addresses.data?.map((a) => (
              <li key={a.id}>
                <span className="capitalize font-medium">{a.label}</span> · {a.line1}, {a.city}
                {a.is_default && (
                  <span className="ml-2 text-xs text-emerald-700">(default)</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
