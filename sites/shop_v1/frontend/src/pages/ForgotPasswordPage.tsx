/* SPDX-License-Identifier: Apache-2.0 */
import { useState } from "react";
import { api } from "../api/client";

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = (e.currentTarget.elements.namedItem("email") as HTMLInputElement).value;
    try {
      await api("/api/auth/password-reset", { method: "POST", body: { email } });
    } catch {
      // intentionally swallow to avoid email enumeration
    }
    setSubmitted(true);
  };

  return (
    <div className="max-w-md mx-auto card p-6 space-y-4">
      <h1 className="text-2xl font-bold">Reset your password</h1>
      {submitted ? (
        <p className="text-sm" data-testid="reset-confirmation">
          If the address is registered, you will receive a reset email shortly.
        </p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label htmlFor="email" className="label">
              Email
            </label>
            <input id="email" name="email" type="email" required className="input" />
          </div>
          <button type="submit" className="btn btn-primary w-full">
            Send reset instructions
          </button>
        </form>
      )}
    </div>
  );
}
