/* SPDX-License-Identifier: Apache-2.0 */
import { Disclosure, Menu, Transition } from "@headlessui/react";
import { Fragment, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCart, useLogout, useMe } from "../api/hooks";
import { CartDrawer } from "./CartDrawer";

export function Layout() {
  const me = useMe();
  const cart = useCart();
  const logout = useLogout();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const cartCount = cart.data?.items.reduce((n, it) => n + it.quantity, 0) ?? 0;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 sticky top-0 z-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link to="/" className="font-bold text-xl shrink-0">
            Acme Shop
          </Link>

          <nav aria-label="Primary" className="hidden md:flex gap-6 text-sm ml-6">
            <NavLink to="/products" className="hover:text-brand-700">
              Products
            </NavLink>
            <NavLink to="/search" className="hover:text-brand-700">
              Search
            </NavLink>
            <NavLink to="/account" className="hover:text-brand-700">
              Account
            </NavLink>
          </nav>

          <form
            role="search"
            className="ml-auto hidden md:block flex-1 max-w-sm"
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const q = (form.elements.namedItem("q") as HTMLInputElement)?.value ?? "";
              navigate(`/search?q=${encodeURIComponent(q)}`);
            }}
          >
            <label htmlFor="header-search" className="sr-only">
              Search products
            </label>
            <input
              id="header-search"
              name="q"
              type="search"
              placeholder="Search products"
              aria-label="Search products"
              className="input"
            />
          </form>

          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label={`Open cart, ${cartCount} item${cartCount === 1 ? "" : "s"}`}
            className="btn btn-secondary relative ml-auto md:ml-0"
          >
            Cart
            {cartCount > 0 && (
              <span
                aria-hidden
                className="ml-1 inline-flex items-center justify-center rounded-full bg-brand-600 text-white text-xs w-5 h-5"
              >
                {cartCount}
              </span>
            )}
          </button>

          {me.data?.authenticated ? (
            <Menu as="div" className="relative">
              <Menu.Button className="btn btn-secondary" aria-label="Account menu">
                {me.data.user?.full_name.split(" ")[0] ?? "Account"}
              </Menu.Button>
              <Transition as={Fragment} enter="transition ease-out duration-100">
                <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-md card shadow-lg focus:outline-none">
                  <div className="py-1">
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          to="/account"
                          className={`block px-4 py-2 text-sm ${active ? "bg-slate-100" : ""}`}
                        >
                          My Account
                        </Link>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          to="/account/orders"
                          className={`block px-4 py-2 text-sm ${active ? "bg-slate-100" : ""}`}
                        >
                          Orders
                        </Link>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={() => logout.mutate()}
                          className={`w-full text-left block px-4 py-2 text-sm ${active ? "bg-slate-100" : ""}`}
                        >
                          Sign out
                        </button>
                      )}
                    </Menu.Item>
                  </div>
                </Menu.Items>
              </Transition>
            </Menu>
          ) : (
            <Link
              to="/login"
              aria-label="Sign in (header)"
              className="btn btn-secondary hidden md:inline-flex"
            >
              Sign in
            </Link>
          )}

          <Disclosure as="div" className="md:hidden">
            <Disclosure.Button
              className="btn btn-secondary"
              aria-label="Toggle navigation menu"
            >
              Menu
            </Disclosure.Button>
            <Disclosure.Panel className="absolute left-0 right-0 top-full bg-white border-b border-slate-200">
              <nav aria-label="Mobile" className="px-4 py-3 flex flex-col gap-2 text-sm">
                <NavLink to="/products">Products</NavLink>
                <NavLink to="/search">Search</NavLink>
                <NavLink to="/account">Account</NavLink>
                {!me.data?.authenticated && <NavLink to="/login">Sign in</NavLink>}
              </nav>
            </Disclosure.Panel>
          </Disclosure>
        </div>
      </header>

      <main role="main" className="max-w-7xl mx-auto px-4 py-8 flex-1 w-full">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-6 text-sm text-slate-500">
          &copy; Acme Shop · synthetic site for revar
        </div>
      </footer>

      <CartDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
