/* SPDX-License-Identifier: Apache-2.0 */
/**
 * Minimal fetch wrapper that:
 *  - threads cookies (credentials: include)
 *  - reads the csrf cookie and echoes it via X-CSRF-Token on mutating methods
 *  - returns parsed JSON, throws ApiError on non-2xx with the parsed body
 */

const CSRF_COOKIE = "shop_v1_csrf";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

function getCsrfCookie(): string | null {
  const match = document.cookie.match(new RegExp("(?:^| )" + CSRF_COOKIE + "=([^;]+)"));
  return match ? decodeURIComponent(match[1]) : null;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  headers?: Record<string, string>;
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const url = new URL(path, window.location.origin);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers ?? {}),
  };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && method !== "HEAD") {
    const csrf = getCsrfCookie();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(url.pathname + url.search, {
    method,
    headers,
    credentials: "include",
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}
