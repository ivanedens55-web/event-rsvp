-- Event RSVP: tables, constraints, indexes and the restricted app role.
-- Run ONCE as the database owner (Supabase SQL editor runs as "postgres").
-- Safe to re-run: every statement checks whether the object already exists.
-- Tables are prefixed "rsvp_" because they share one Supabase project with other apps.

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rsvp_hosts (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- Stored lowercase so "Ann@x.com" and "ann@x.com" are the same account.
    email         TEXT NOT NULL UNIQUE
                  CHECK (email = lower(email) AND char_length(email) BETWEEN 3 AND 254),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rsvp_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host_id     BIGINT NOT NULL REFERENCES rsvp_hosts (id) ON DELETE CASCADE,
    -- Random token used in the public link. Unguessable, so the integer id stays private.
    slug        TEXT NOT NULL UNIQUE CHECK (slug ~ '^[A-Za-z0-9_-]{8,32}$'),
    title       TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120),
    description TEXT NOT NULL DEFAULT '' CHECK (char_length(description) <= 2000),
    location    TEXT NOT NULL DEFAULT '' CHECK (char_length(location) <= 200),
    starts_at   TIMESTAMPTZ NOT NULL,
    -- NULL means "no limit". Counts people (party sizes), not RSVPs.
    capacity    INTEGER CHECK (capacity IS NULL OR capacity BETWEEN 1 AND 10000),
    rsvp_open   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rsvp_responses (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   BIGINT NOT NULL REFERENCES rsvp_events (id) ON DELETE CASCADE,
    name       TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100),
    email      TEXT NOT NULL
               CHECK (email = lower(email) AND char_length(email) BETWEEN 3 AND 254),
    response   TEXT NOT NULL CHECK (response IN ('yes', 'no', 'maybe')),
    party_size SMALLINT NOT NULL DEFAULT 1 CHECK (party_size BETWEEN 1 AND 10),
    note       TEXT NOT NULL DEFAULT '' CHECK (char_length(note) <= 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- One RSVP per email per event. The database enforces this even if two
    -- requests arrive at the same moment.
    CONSTRAINT rsvp_responses_one_per_email UNIQUE (event_id, email)
);

-- ---------------------------------------------------------------------------
-- Indexes
-- (UNIQUE and PRIMARY KEY columns already get an index automatically:
--  rsvp_hosts.email for login lookups, rsvp_events.slug for public-link lookups.)
-- ---------------------------------------------------------------------------

-- Foreign key + the dashboard query "my events, soonest first":
-- WHERE host_id = $1 ORDER BY starts_at. Also speeds up ON DELETE CASCADE from hosts.
CREATE INDEX IF NOT EXISTS rsvp_events_host_id_starts_at_idx
    ON rsvp_events (host_id, starts_at);

-- No separate index on rsvp_responses.event_id: the UNIQUE (event_id, email)
-- constraint creates an index whose first column is event_id, so it already
-- serves "all RSVPs for this event", the counts query and the FK cascade.

-- ---------------------------------------------------------------------------
-- Restricted app role (least privilege)
-- The backend connects as rsvp_app. It can read and write rows in its own
-- three tables and nothing else: no CREATE, DROP, ALTER or TRUNCATE.
-- Set its password separately so no secret lives in this file:
--   ALTER ROLE rsvp_app WITH PASSWORD 'a-long-random-password';
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rsvp_app') THEN
        CREATE ROLE rsvp_app LOGIN NOINHERIT;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO rsvp_app;
REVOKE CREATE ON SCHEMA public FROM rsvp_app;

-- Supabase auto-grants new tables to its Data API roles. This app doesn't use
-- the Data API, so take those grants back (skipped on plain Postgres).
DO $$
DECLARE r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('REVOKE ALL ON rsvp_hosts, rsvp_events, rsvp_responses FROM %I', r);
        END IF;
    END LOOP;
END
$$;

GRANT SELECT, INSERT, UPDATE ON rsvp_hosts TO rsvp_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON rsvp_events TO rsvp_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON rsvp_responses TO rsvp_app;

-- ---------------------------------------------------------------------------
-- Row-level security
-- RLS is on so Supabase's anon/authenticated roles (Data API) can never read
-- these tables. The only policy lets rsvp_app through; the backend then
-- checks ownership on every protected route (WHERE host_id = <current host>).
-- ---------------------------------------------------------------------------

ALTER TABLE rsvp_hosts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvp_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvp_responses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rsvp_app_all ON rsvp_hosts;
CREATE POLICY rsvp_app_all ON rsvp_hosts     TO rsvp_app USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS rsvp_app_all ON rsvp_events;
CREATE POLICY rsvp_app_all ON rsvp_events    TO rsvp_app USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS rsvp_app_all ON rsvp_responses;
CREATE POLICY rsvp_app_all ON rsvp_responses TO rsvp_app USING (true) WITH CHECK (true);
