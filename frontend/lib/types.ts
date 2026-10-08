// Shapes returned by the backend. Mirrors docs/openapi.yaml.

export type Answer = "yes" | "no" | "maybe";

export type Counts = { yes: number; no: number; maybe: number; attending: number };

export type HostEvent = {
  id: number;
  slug: string;
  title: string;
  description: string;
  location: string;
  starts_at: string;
  capacity: number | null;
  rsvp_open: boolean;
  accepting_rsvps: boolean;
  counts: Counts;
  created_at: string;
};

export type PublicEvent = {
  slug: string;
  title: string;
  description: string;
  location: string;
  starts_at: string;
  accepting_rsvps: boolean;
  spots_left: number | null;
};

export type Rsvp = {
  id: number;
  name: string;
  email: string;
  response: Answer;
  party_size: number;
  note: string;
  created_at: string;
};

export type EventInput = {
  title: string;
  description: string;
  location: string;
  starts_at: string;
  capacity: number | null;
};
