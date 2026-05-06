/* SPDX-License-Identifier: Apache-2.0 */
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "./client";
import type {
  Address,
  AuthMe,
  Cart,
  CheckoutReview,
  OrderDetail,
  OrderListPage,
  Product,
  ProductPage,
  ProductSearchPage,
  Category,
} from "./types";

// ----- catalog -----

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Category[]>("/api/categories"),
  });
}

export interface ProductFilters {
  category?: string;
  q?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  sort?: string;
  page?: number;
}

export function useProducts(filters: ProductFilters) {
  return useQuery({
    queryKey: ["products", filters],
    queryFn: () =>
      api<ProductPage>("/api/products", {
        query: {
          ...filters,
          per_page: 12,
        },
      }),
  });
}

export function useProductSearch(q: string) {
  return useInfiniteQuery({
    queryKey: ["product-search", q],
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page: ProductSearchPage) => page.next_cursor ?? undefined,
    queryFn: ({ pageParam }) =>
      api<ProductSearchPage>("/api/products/search", {
        query: { q, cursor: pageParam, limit: 12 },
      }),
    enabled: q.trim().length > 0,
  });
}

export function useProduct(slug: string) {
  return useQuery({
    queryKey: ["product", slug],
    queryFn: () => api<Product>(`/api/products/${encodeURIComponent(slug)}`),
    enabled: !!slug,
  });
}

// ----- cart -----

export function useCart() {
  return useQuery({
    queryKey: ["cart"],
    queryFn: () => api<Cart>("/api/cart"),
  });
}

export function useAddToCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { product_id: number; quantity?: number }) =>
      api<Cart>("/api/cart/items", { method: "POST", body: vars }),
    onSuccess: (data) => qc.setQueryData(["cart"], data),
  });
}

export function useUpdateCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { item_id: number; quantity: number }) =>
      api<Cart>(`/api/cart/items/${vars.item_id}`, {
        method: "PATCH",
        body: { quantity: vars.quantity },
      }),
    onSuccess: (data) => qc.setQueryData(["cart"], data),
  });
}

export function useRemoveCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (item_id: number) =>
      api<Cart>(`/api/cart/items/${item_id}`, { method: "DELETE" }),
    onSuccess: (data) => qc.setQueryData(["cart"], data),
  });
}

export function useApplyCartCoupon() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      api<{ ok: boolean; applied_at_checkout: boolean; message: string; cart: Cart }>(
        "/api/cart/coupon",
        { method: "POST", body: { code } },
      ),
    onSuccess: (data) => qc.setQueryData(["cart"], data.cart),
  });
}

// ----- auth -----

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<AuthMe>("/api/auth/me"),
    staleTime: 0,
  });
}

export function useSignup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { email: string; password: string; full_name: string }) =>
      api("/api/auth/signup", { method: "POST", body: vars }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { email: string; password: string }) =>
      api("/api/auth/login", { method: "POST", body: vars }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api("/api/auth/logout", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

// ----- checkout -----

export function useCheckoutStart() {
  return useMutation({
    mutationFn: () => api<{ order_id: number; subtotal_cents: number }>("/api/checkout/start", {
      method: "POST",
    }),
  });
}

export function useCheckoutShipping() {
  return useMutation({
    mutationFn: (vars: { address_id: number }) =>
      api("/api/checkout/shipping", { method: "PATCH", body: vars }),
  });
}

export function useCheckoutCoupon() {
  return useMutation({
    mutationFn: (code: string) =>
      api<{
        ok: boolean;
        applied_at_checkout: boolean;
        coupon: string;
        discount_cents: number;
        total_cents: number;
      }>("/api/checkout/coupon", { method: "POST", body: { code } }),
  });
}

export function useCheckoutReview() {
  return useQuery({
    queryKey: ["checkout-review"],
    queryFn: () => api<CheckoutReview>("/api/checkout/review"),
    staleTime: 0,
    retry: false,
  });
}

export function useCheckoutConfirm() {
  return useMutation({
    mutationFn: (vars: { card_number: string; card_exp: string; card_cvc: string }) =>
      api<{
        status: string;
        order_id?: number;
        total_cents?: number;
        paid_at?: string;
        redirect_url?: string;
      }>("/api/checkout/confirm", { method: "POST", body: vars }),
  });
}

// ----- account -----

export function useOrders(page: number) {
  return useQuery({
    queryKey: ["orders", page],
    queryFn: () => api<OrderListPage>("/api/account/orders", { query: { page } }),
  });
}

export function useOrder(id: number) {
  return useQuery({
    queryKey: ["order", id],
    queryFn: () => api<OrderDetail>(`/api/account/orders/${id}`),
    enabled: !!id,
  });
}

export function useAddresses() {
  return useQuery({
    queryKey: ["addresses"],
    queryFn: () => api<Address[]>("/api/account/addresses"),
  });
}
