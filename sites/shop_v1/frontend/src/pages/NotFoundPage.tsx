/* SPDX-License-Identifier: Apache-2.0 */
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="card p-12 text-center space-y-3">
      <p className="text-6xl font-bold text-slate-300">404</p>
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="text-slate-500">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="btn btn-primary inline-block">
        Back home
      </Link>
    </div>
  );
}
