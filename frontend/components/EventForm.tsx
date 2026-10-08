"use client";

import { FormEvent, useState } from "react";
import { errorMessage } from "@/lib/api";
import { isoToLocalInput, localInputToIso } from "@/lib/format";
import type { EventInput, HostEvent } from "@/lib/types";

type Props = {
  initial?: HostEvent;
  submitLabel: string;
  onSubmit: (input: EventInput) => Promise<void>;
  onCancel?: () => void;
};

// Collects input only. The backend validates everything again and decides
// what's allowed (e.g. a capacity below the people already coming).
export default function EventForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [startsAt, setStartsAt] = useState(initial ? isoToLocalInput(initial.starts_at) : "");
  const [capacity, setCapacity] = useState(initial?.capacity?.toString() ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit({
        title,
        description,
        location,
        starts_at: localInputToIso(startsAt),
        capacity: capacity === "" ? null : Number(capacity),
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="panel">
      {error && <p className="error" role="alert">{error}</p>}
      <label>
        Event name
        <input required maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <div className="row">
        <label>
          Starts
          <input type="datetime-local" required value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)} />
        </label>
        <label>
          Spots <span className="hint">(leave empty for no limit)</span>
          <input type="number" min={1} max={10000} value={capacity}
            onChange={(e) => setCapacity(e.target.value)} />
        </label>
      </div>
      <label>
        Where <span className="hint">(optional)</span>
        <input maxLength={200} value={location} onChange={(e) => setLocation(e.target.value)} />
      </label>
      <label>
        Details for guests <span className="hint">(optional)</span>
        <textarea maxLength={2000} value={description}
          onChange={(e) => setDescription(e.target.value)} />
      </label>
      <div className="actions">
        <button type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="secondary" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}
