// The JWT lives in localStorage. Trade-off explained in the README:
// simple and works across domains (Vercel -> Render), but readable by any
// script on the page, so we keep the token short-lived and set a strict CSP.

const KEY = "rsvp_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function saveToken(token: string): void {
  window.localStorage.setItem(KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(KEY);
}
