import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Event RSVP",
  description: "Create an event, share one link, see who's coming.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
