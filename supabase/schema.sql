-- ============================================================
-- NCPL Ticketing Tool — Supabase Schema
-- Run this in: Supabase Dashboard > SQL Editor > New Query
-- ============================================================


-- ─── USERS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    user_id       TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT,
    picture       TEXT,
    role          TEXT NOT NULL DEFAULT 'employee',
    department    TEXT,
    created_at    TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ
);


-- ─── USER SESSIONS ───────────────────────────────────────────
-- Stores custom session tokens issued after Google OAuth login.
CREATE TABLE IF NOT EXISTS public.user_sessions (
    session_token TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    expires_at    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ
);


-- ─── DEPARTMENTS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.departments (
    id          TEXT PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ
);


-- ─── TICKETS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tickets (
    id               TEXT PRIMARY KEY,
    code             TEXT UNIQUE,
    title            TEXT,
    description      TEXT,
    status           TEXT DEFAULT 'Open',
    priority         TEXT DEFAULT 'Medium',
    department       TEXT,
    created_by       TEXT,
    created_by_name  TEXT,
    created_by_email TEXT,
    assignee_id      TEXT,
    assignee_name    TEXT,
    due_at           TIMESTAMPTZ,
    is_escalated     SMALLINT DEFAULT 0,
    escalated_at     TIMESTAMPTZ,
    resolved_at      TIMESTAMPTZ,
    closed_at        TIMESTAMPTZ,
    created_at       TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ
);


-- ─── COMMENTS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.comments (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT REFERENCES public.tickets(id) ON DELETE CASCADE,
    body        TEXT,
    is_internal SMALLINT DEFAULT 0,
    author_id   TEXT,
    author_name TEXT,
    author_role TEXT,
    created_at  TIMESTAMPTZ
);


-- ─── ATTACHMENTS ─────────────────────────────────────────────
-- File data is stored as BYTEA (binary). Max 15 MB per attachment
-- is enforced at the application layer, not here.
CREATE TABLE IF NOT EXISTS public.attachments (
    id               TEXT PRIMARY KEY,
    ticket_id        TEXT REFERENCES public.tickets(id) ON DELETE CASCADE,
    filename         TEXT,
    content_type     TEXT,
    size             INTEGER,
    data             BYTEA,
    uploaded_by      TEXT,
    uploaded_by_name TEXT,
    created_at       TIMESTAMPTZ,
    is_deleted       SMALLINT DEFAULT 0
);


-- ─── TICKET COUNTER ──────────────────────────────────────────
-- Tracks the last-used ticket number for NCP-XXXX codes.
CREATE TABLE IF NOT EXISTS public.ticket_counter (
    id    INTEGER PRIMARY KEY DEFAULT 1,
    value INTEGER DEFAULT 0
);
INSERT INTO public.ticket_counter (id, value)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;


-- ─── INDEXES ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id    ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON public.user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_tickets_status           ON public.tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_department       ON public.tickets(department);
CREATE INDEX IF NOT EXISTS idx_tickets_created_by       ON public.tickets(created_by);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee_id      ON public.tickets(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at       ON public.tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_ticket_id       ON public.comments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_attachments_ticket_id    ON public.attachments(ticket_id);


-- ─── SEED DEPARTMENTS ────────────────────────────────────────
INSERT INTO public.departments (id, name, description, created_at) VALUES
    ('dept_hr000000000000', 'HR',        'HR department',        NOW()),
    ('dept_sa000000000000', 'Sales',     'Sales department',     NOW()),
    ('dept_tr000000000000', 'Training',  'Training department',  NOW()),
    ('dept_me000000000000', 'Mentoring', 'Mentoring department', NOW()),
    ('dept_fi000000000000', 'Finance',   'Finance department',   NOW()),
    ('dept_hu000000000000', 'Hrudai',    'Hrudai department',    NOW())
ON CONFLICT (name) DO NOTHING;


-- ─── ROW LEVEL SECURITY (RLS) ────────────────────────────────
-- The FastAPI backend connects using the SERVICE ROLE key, so RLS
-- is safe to leave disabled. If you ever query Supabase directly
-- from the browser (anon key), enable RLS and add policies below.
--
-- ALTER TABLE public.users             ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.user_sessions     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.departments       ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.tickets           ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.comments          ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.attachments       ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.ticket_counter    ENABLE ROW LEVEL SECURITY;
