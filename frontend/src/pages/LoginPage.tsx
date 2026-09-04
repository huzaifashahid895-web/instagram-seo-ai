import { FormEvent, useState } from "react";

type LoginPageProps = {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, fullName: string) => Promise<void>;
};

export function LoginPage({ onLogin, onRegister }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "register" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      if (mode === "register") {
        await onRegister(email, password, fullName);
      } else if (mode === "reset") {
        // Password reset
        const response = await fetch("http://localhost:8000/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, new_password: password }),
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "Password reset failed");
        }
        setSuccess("Password reset successfully! You can now log in.");
        setMode("login");
        setPassword("");
      } else {
        await onLogin(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10 text-slate-950">
      <section className="w-full max-w-sm rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">AISM</p>
          <h1 className="mt-1 text-2xl font-semibold">
            {mode === "reset" ? "Reset Password" : "Sign in"}
          </h1>
        </div>

        <div className="mb-5 grid grid-cols-3 rounded-md bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => { setMode("login"); setError(null); setSuccess(null); }}
            className={`h-9 rounded px-2 text-xs font-medium ${mode === "login" ? "bg-white shadow-sm" : "text-slate-600"}`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(null); setSuccess(null); }}
            className={`h-9 rounded px-2 text-xs font-medium ${mode === "register" ? "bg-white shadow-sm" : "text-slate-600"}`}
          >
            Register
          </button>
          <button
            type="button"
            onClick={() => { setMode("reset"); setError(null); setSuccess(null); }}
            className={`h-9 rounded px-2 text-xs font-medium ${mode === "reset" ? "bg-white shadow-sm" : "text-slate-600"}`}
          >
            Reset
          </button>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {mode === "register" && (
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Full name</span>
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              />
            </label>
          )}
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              {mode === "reset" ? "New Password" : "Password"}
            </span>
            <input
              type="password"
              required
              minLength={mode === "register" || mode === "reset" ? 8 : 1}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
            />
          </label>
          {success && <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{success}</p>}
          {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <button
            type="submit"
            disabled={isSubmitting}
            className="h-10 w-full rounded-md bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isSubmitting ? "Working..." : mode === "register" ? "Create account" : mode === "reset" ? "Reset password" : "Login"}
          </button>
        </form>
      </section>
    </main>
  );
}
