/* SPDX-License-Identifier: Apache-2.0 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { useSignup } from "../api/hooks";

const schema = z.object({
  full_name: z.string().min(1, "Required").max(120),
  email: z.string().email(),
  password: z.string().min(8, "At least 8 characters").max(128),
});

export function SignupPage() {
  const signup = useSignup();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = params.get("redirect") ?? "/account";

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: z.infer<typeof schema>) => {
    try {
      await signup.mutateAsync(data);
      navigate(redirect);
    } catch (err: any) {
      if (err?.detail === "email_taken") {
        setError("email", { message: "Email already registered" });
      } else {
        setError("root" as any, { message: "Could not create account" });
      }
    }
  };

  return (
    <div className="max-w-md mx-auto card p-6 space-y-4">
      <h1 className="text-2xl font-bold">Create your account</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        <div>
          <label htmlFor="full_name" className="label">
            Full name
          </label>
          <input id="full_name" autoComplete="name" className="input" {...register("full_name")} />
          {errors.full_name && (
            <p className="text-xs text-rose-600 mt-1">{errors.full_name.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="email" className="label">
            Email
          </label>
          <input id="email" type="email" autoComplete="email" className="input" {...register("email")} />
          {errors.email && <p className="text-xs text-rose-600 mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label htmlFor="password" className="label">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            className="input"
            {...register("password")}
          />
          {errors.password && (
            <p className="text-xs text-rose-600 mt-1">{errors.password.message}</p>
          )}
        </div>
        <button type="submit" className="btn btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-slate-500">
        Already have an account?{" "}
        <Link to={`/login${redirect !== "/account" ? `?redirect=${redirect}` : ""}`}>
          Sign in
        </Link>
      </p>
    </div>
  );
}
