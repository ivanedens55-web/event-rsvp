"use client";

import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Answer, PublicEvent } from "@/lib/types";

const ANSWERS: { value: Answer; label: string }[] = [
  { value: "yes", label: "Going" },
  { value: "maybe", label: "Maybe" },
  { value: "no", label: "Can't go" },
];

type Confirmation = { name: string; response: Answer; party_size: number };

export default function PublicRsvpPage() {
  const { slug } = useParams<{ slug: string }>();
  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [loadError, setLoadError] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [answer, setAnswer] = useState<Answer>("yes");
  const [partySize, setPartySize] = useState(1);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Confirmation | null>(null);

  useEffect(() => {
    api<PublicEvent>(`/public/events/${encodeURIComponent(slug)}`)
      .then(setEvent)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [slug]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<Confirmation>(`/public/events/${encodeURIComponent(slug)}/rsvps`, {
        method: "POST",
        body: { name, email, response: answer, party_size: partySize, note },
      });
      setDone(result);
    } catch (err) {
      setError(errorMessage(err)); // e.g. "This event is full." straight from the backend
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return <main className="page"><div className="ticket ticket-top"><p className="error">{loadError}</p></div></main>;
  }
  if (!event) {
    return <main className="page"><p className="muted" style={{ textAlign: "center" }}>Loading invitation…</p></main>;
  }

  return (
    <main className="page">
      <article className="ticket">
        <div className="ticket-top">
          <h1>{event.title}</h1>
          <div className="ticket-meta">
            <span><strong>When</strong> {formatDateTime(event.starts_at)}</span>
            {event.location && <span><strong>Where</strong> {event.location}</span>}
            {event.spots_left !== null && event.accepting_rsvps && (
              <span><strong>Spots left</strong> {event.spots_left}</span>
            )}
          </div>
          {event.description && <p style={{ marginTop: "1rem", whiteSpace: "pre-line" }}>{event.description}</p>}
        </div>

        <div className="perforation" aria-hidden="true" />

        <div className="ticket-bottom">
          {done ? (
            <div role="status">
              <span className={`stamp ${done.response}`}>
                {ANSWERS.find((a) => a.value === done.response)?.label}
              </span>
              <p>
                Thanks, {done.name}. Your reply is saved
                {done.response === "yes" && done.party_size > 1 ? ` for ${done.party_size} people` : ""}.
                The host can see it now.
              </p>
            </div>
          ) : !event.accepting_rsvps ? (
            <p className="notice" style={{ margin: 0 }}>
              This event isn't taking RSVPs anymore. Contact the host if you need to reply.
            </p>
          ) : (
            <form onSubmit={submit}>
              {error && <p className="error" role="alert">{error}</p>}
              <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                <legend style={{ fontWeight: 600 }}>Your reply</legend>
                <div className="answers">
                  {ANSWERS.map((a) => (
                    <label key={a.value} className={`${a.value} ${answer === a.value ? "checked" : ""}`}>
                      <input type="radio" name="answer" value={a.value}
                        checked={answer === a.value} onChange={() => setAnswer(a.value)} />
                      <span>{a.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="row">
                <label>
                  Your name
                  <input required maxLength={100} autoComplete="name"
                    value={name} onChange={(e) => setName(e.target.value)} />
                </label>
                <label>
                  Email <span className="hint">(only the host sees it)</span>
                  <input type="email" required maxLength={254} autoComplete="email"
                    value={email} onChange={(e) => setEmail(e.target.value)} />
                </label>
              </div>
              {answer !== "no" && (
                <label>
                  People in your group, including you
                  <input type="number" min={1} max={10} required value={partySize}
                    onChange={(e) => setPartySize(Number(e.target.value))} />
                </label>
              )}
              <label>
                Note for the host <span className="hint">(optional)</span>
                <textarea maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
              </label>
              <button type="submit" disabled={busy}>{busy ? "Sending…" : "Send reply"}</button>
              <p className="muted small" style={{ marginTop: "1rem", marginBottom: 0 }}>
                One reply per email. No account needed.
              </p>
            </form>
          )}
        </div>
      </article>
    </main>
  );
}
