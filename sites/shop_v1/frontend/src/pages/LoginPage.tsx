/* SPDX-License-Identifier: Apache-2.0 */
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useLogin } from "../api/hooks";

export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = params.get("redirect") ?? "/account";
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    const form = e.currentTarget;
    const email = (form.elements.namedItem("email") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;
    try {
      await login.mutateAsync({ email, password });
      navigate(redirect);
    } catch (err: any) {
      setError("Invalid email or password.");
    }
  };

  return (
    <div className="max-w-md mx-auto card p-6 space-y-4">
      <h1 className="text-2xl font-bold">Sign in</h1>
      {error && (
        <p role="alert" className="text-sm text-rose-700">
          {error}
        </p>
      )}
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label htmlFor="email" className="label">
            Email
          </label>
          <input id="email" name="email" type="email" autoComplete="email" required className="input" />
        </div>
        <div>
          <label htmlFor="password" className="label">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="input"
          />
        </div>
        <button type="submit" className="btn btn-primary w-full" disabled={login.isPending}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="text-sm text-slate-500 flex justify-between">
        <Link to="/forgot-password">Forgot password?</Link>
        <Link to={`/signup${redirect !== "/account" ? `?redirect=${redirect}` : ""}`}>
          Create account
        </Link>
      </div>
    </div>
  );
}
