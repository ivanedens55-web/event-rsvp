"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import EventForm from "@/components/EventForm";
import HostTopbar from "@/components/HostTopbar";
import { api, ApiError, errorMessage } from "@/lib/api";
import { dayAndMonth, formatDateTime } from "@/lib/format";
import type { EventInput, HostEvent } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function Dashboard() {
  const ready = useRequireAuth();
  const router = useRouter();
  const [events, setEvents] = useState<HostEvent[] | null>(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!ready) return;
    api<HostEvent[]>("/events", { auth: true })
      .then(setEvents)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(errorMessage(err));
      });
  }, [ready, router]);

  async function createEvent(input: EventInput) {
    const created = await api<HostEvent>("/events", { method: "POST", body: input, auth: true });
    router.push(`/dashboard/events/${created.id}`);
  }

  if (!ready) return null;

  return (
    <main className="page">
      <HostTopbar />
      <div className="topbar" style={{ marginBottom: "1rem" }}>
        <h1 style={{ margin: 0 }}>Your events</h1>
        {!creating && <button onClick={() => setCreating(true)}>New event</button>}
      </div>

      {creating && (
        <div style={{ marginBottom: "2rem" }}>
          <EventForm submitLabel="Create event" onSubmit={createEvent}
            onCancel={() => setCreating(false)} />
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}
      {events === null && !error && <p className="muted">Loading your events…</p>}
      {events?.length === 0 && (
        <p className="empty">No events yet. Create one, then share its link with your guests.</p>
      )}

      {events && events.length > 0 && (
        <ul className="event-list">
          {events.map((ev) => {
            const { day, month } = dayAndMonth(ev.starts_at);
            return (
              <li key={ev.id}>
                <Link href={`/dashboard/events/${ev.id}`} className="event-row">
                  <span className="date-block">
                    <span className="day">{day}</span>
                    <span className="month">{month}</span>
                  </span>
                  <span>
                    <span className="event-title">{ev.title}</span>
                    <span className="muted small" style={{ display: "block" }}>
                      {formatDateTime(ev.starts_at)}
                      {ev.location && `, ${ev.location}`}
                      {!ev.accepting_rsvps && " (not taking RSVPs)"}
                    </span>
                  </span>
                  <span className="headcount">
                    <strong>{ev.counts.attending}</strong>
                    <span className="muted small">
                      {ev.capacity ? ` / ${ev.capacity}` : ""} coming
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
