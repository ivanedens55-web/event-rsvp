"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken } from "./auth";

/** Send logged-out visitors to /login. Returns true once a token is present. */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (getToken()) setReady(true);
    else router.replace("/login");
  }, [router]);
  return ready;
}
