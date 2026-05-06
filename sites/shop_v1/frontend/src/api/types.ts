/* SPDX-License-Identifier: Apache-2.0 */

export interface Category {
  slug: string;
  name: string;
  description: string;
}

export interface Product {
  id: number;
  slug: string;
  name: string;
  short_description: string;
  description?: string;
  price_cents: number;
  currency: string;
  stock: number;
  image_url: string;
  category_id: number;
  category?: { slug: string; name: string };
  rating: number;
  rating_count: number;
  tags: string[];
}

export interface ProductPage {
  items: Product[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface ProductSearchPage {
  items: Product[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface CartItem {
  id: number;
  product_id: number;
  slug: string;
  name: string;
  image_url: string;
  unit_price_cents: number;
  quantity: number;
  line_total_cents: number;
  in_stock: boolean;
}

export interface Cart {
  items: CartItem[];
  subtotal_cents: number;
  coupon_code: string | null;
  cart_coupon_attempt: string | null;
  updated_at: string | null;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface AuthMe {
  authenticated: boolean;
  user?: User;
  csrf_token: string;
}

export interface Address {
  id: number;
  label: string;
  full_name: string;
  line1: string;
  line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export interface ReviewItem {
  product_id: number;
  name: string;
  unit_price_cents: number;
  quantity: number;
  line_total_cents: number;
  in_stock: boolean;
}

export interface CheckoutReview {
  order_id: number;
  items: ReviewItem[];
  subtotal_cents: number;
  discount_cents: number;
  total_cents: number;
  coupon_code: string | null;
  shipping_address: Address | null;
  out_of_stock_items: ReviewItem[];
}

export interface OrderSummary {
  id: number;
  status: string;
  total_cents: number;
  created_at: string | null;
}

export interface OrderListPage {
  items: OrderSummary[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface OrderDetail extends OrderSummary {
  subtotal_cents: number;
  discount_cents: number;
  coupon_code: string | null;
  payment_attempts: number;
  last_payment_error: string | null;
  paid_at: string | null;
  items: {
    product_id: number;
    product_name: string;
    unit_price_cents: number;
    quantity: number;
  }[];
}
