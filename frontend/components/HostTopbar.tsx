"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

export default function HostTopbar() {
  const router = useRouter();
  function logOut() {
    clearToken();
    router.push("/login");
  }
  return (
    <nav className="topbar">
      <Link href="/dashboard" className="brand">Event RSVP</Link>
      <button type="button" className="link" onClick={logOut}>Log out</button>
    </nav>
  );
}
