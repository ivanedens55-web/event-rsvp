"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { saveToken } from "@/lib/auth";

type Mode = "login" | "register";

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { access_token } = await api<{ access_token: string }>(`/auth/${mode}`, {
        method: "POST",
        body: { email, password },
      });
      saveToken(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const isLogin = mode === "login";
  return (
    <main className="page narrow">
      <nav className="topbar">
        <Link href="/" className="brand">Event RSVP</Link>
      </nav>
      <div className="panel">
        <h2>{isLogin ? "Log in" : "Create a host account"}</h2>
        <p className="muted small">Guests never need an account. This is only for hosts.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <form onSubmit={onSubmit}>
          <label>
            Email
            <input type="email" required maxLength={254} autoComplete="email"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password <span className="hint">{isLogin ? "" : "(8 or more characters)"}</span>
            <input type="password" required minLength={8} maxLength={128}
              autoComplete={isLogin ? "current-password" : "new-password"}
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}
          </button>
        </form>
        <p className="small" style={{ marginTop: "1.25rem", marginBottom: 0 }}>
          {isLogin
            ? <>No account yet? <Link href="/register">Create one</Link></>
            : <>Already have an account? <Link href="/login">Log in</Link></>}
        </p>
      </div>
    </main>
  );
}
