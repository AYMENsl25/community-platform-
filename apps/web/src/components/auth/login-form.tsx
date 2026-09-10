"use client";

import { useState, type FormEvent } from "react";
import { translate, type LocaleCode } from "@talaqi/translations";

export function LoginForm({
  locale,
  returnTo,
}: {
  locale: LocaleCode;
  returnTo: string;
}) {
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setFailed(false);
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/public/api/v1/auth/login", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identifier: String(data.get("identifier") ?? ""),
          password: String(data.get("password") ?? ""),
        }),
      });
      if (!response.ok) {
        setFailed(true);
        return;
      }
      window.location.assign(returnTo);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="tq-auth-form" onSubmit={submit}>
      <label htmlFor="login-identifier">
        {translate(locale, "auth.login.identifier")}
      </label>
      <input
        autoComplete="username"
        id="login-identifier"
        name="identifier"
        required
        spellCheck={false}
      />
      <label htmlFor="login-password">
        {translate(locale, "auth.login.password")}
      </label>
      <input
        autoComplete="current-password"
        id="login-password"
        name="password"
        required
        type="password"
      />
      <button disabled={pending} type="submit">
        {translate(
          locale,
          pending ? "auth.login.processing" : "auth.login.submit",
        )}
      </button>
      <p className="tq-auth-error" role="alert">
        {failed ? translate(locale, "auth.login.error") : ""}
      </p>
    </form>
  );
}
