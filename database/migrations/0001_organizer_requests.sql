-- Adds organizer approval workflow for club creation.

BEGIN;

CREATE TABLE IF NOT EXISTS organizer_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending',
  reason text,
  admin_note text,
  reviewed_by uuid REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT organizer_requests_status_valid CHECK (status IN ('pending', 'approved', 'rejected')),
  CONSTRAINT organizer_requests_reason_len CHECK (reason IS NULL OR char_length(reason) <= 1000),
  CONSTRAINT organizer_requests_admin_note_len CHECK (admin_note IS NULL OR char_length(admin_note) <= 1000)
);

DROP TRIGGER IF EXISTS organizer_requests_set_updated_at ON organizer_requests;
CREATE TRIGGER organizer_requests_set_updated_at
BEFORE UPDATE ON organizer_requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS organizer_requests_status_idx ON organizer_requests (status, created_at DESC);
CREATE INDEX IF NOT EXISTS organizer_requests_user_status_idx ON organizer_requests (user_id, status);

COMMIT;
