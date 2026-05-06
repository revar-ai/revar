/* SPDX-License-Identifier: Apache-2.0 */
import { useSearchParams } from "react-router-dom";

export function Pagination({
  page,
  totalPages,
}: {
  page: number;
  totalPages: number;
}) {
  const [params, setParams] = useSearchParams();
  if (totalPages <= 1) return null;

  const setPage = (n: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(n));
    setParams(next);
  };

  // Show up to 5 page numbers around the current
  const window: number[] = [];
  const lo = Math.max(1, page - 2);
  const hi = Math.min(totalPages, lo + 4);
  for (let i = lo; i <= hi; i++) window.push(i);

  return (
    <nav aria-label="Pagination" className="flex items-center gap-1 justify-center mt-8">
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => setPage(Math.max(1, page - 1))}
        disabled={page === 1}
        aria-label="Previous page"
      >
        Prev
      </button>
      {window.map((n) => (
        <button
          key={n}
          type="button"
          aria-current={n === page ? "page" : undefined}
          className={`btn ${n === page ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setPage(n)}
        >
          {n}
        </button>
      ))}
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => setPage(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
        aria-label="Next page"
      >
        Next
      </button>
    </nav>
  );
}
