-- COMMUNITI PostgreSQL 17 schema
-- Run this file while connected to the communiti_dev database.
-- Required extensions now: pgcrypto, citext, pg_trgm.
-- Optional AI extension later: vector(pgvector).

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- pgvector is optional for the first local setup.
-- Enable this later after installing pgvector on the PostgreSQL server:
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE user_platform_role AS ENUM ('user', 'admin');
CREATE TYPE club_visibility AS ENUM ('public', 'private');
CREATE TYPE club_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE club_member_role AS ENUM ('owner', 'admin', 'member');
CREATE TYPE club_member_status AS ENUM ('pending', 'active', 'banned', 'left');
CREATE TYPE event_status AS ENUM ('draft', 'published', 'cancelled', 'completed');
CREATE TYPE event_registration_status AS ENUM ('pending', 'confirmed', 'waitlisted', 'cancelled', 'rejected');
CREATE TYPE notification_kind AS ENUM ('system', 'club', 'event', 'registration', 'waitlist');
CREATE TYPE media_owner_type AS ENUM ('user', 'club', 'event');
CREATE TYPE embedding_entity_type AS ENUM ('user', 'club', 'event');
CREATE TYPE recommendation_action AS ENUM ('impression', 'click', 'save', 'register');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_user_id text UNIQUE,
  email citext NOT NULL UNIQUE,
  username citext UNIQUE,
  display_name text NOT NULL,
  avatar_url text,
  bio text,
  city text,
  country text DEFAULT 'Saudi Arabia',
  platform_role user_platform_role NOT NULL DEFAULT 'user',
  is_onboarded boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  CONSTRAINT users_display_name_len CHECK (char_length(display_name) BETWEEN 2 AND 120),
  CONSTRAINT users_bio_len CHECK (bio IS NULL OR char_length(bio) <= 1000)
);

CREATE TABLE organizer_requests (
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

CREATE TABLE user_preferences (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  interest_categories text[] NOT NULL DEFAULT '{}',
  interest_tags text[] NOT NULL DEFAULT '{}',
  preferred_city text,
  max_distance_km integer,
  notify_email boolean NOT NULL DEFAULT true,
  notify_push boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT user_preferences_distance_positive CHECK (max_distance_km IS NULL OR max_distance_km > 0)
);

CREATE TABLE club_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  slug text NOT NULL UNIQUE,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE clubs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  category_id uuid REFERENCES club_categories(id) ON DELETE SET NULL,
  name text NOT NULL,
  slug text NOT NULL UNIQUE,
  description text,
  logo_url text,
  cover_image_url text,
  city text,
  country text DEFAULT 'Saudi Arabia',
  visibility club_visibility NOT NULL DEFAULT 'public',
  status club_status NOT NULL DEFAULT 'draft',
  member_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  CONSTRAINT clubs_name_len CHECK (char_length(name) BETWEEN 3 AND 160),
  CONSTRAINT clubs_description_len CHECK (description IS NULL OR char_length(description) <= 5000),
  CONSTRAINT clubs_member_count_nonnegative CHECK (member_count >= 0)
);

CREATE TABLE club_tags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  slug text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE club_tag_links (
  club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
  tag_id uuid NOT NULL REFERENCES club_tags(id) ON DELETE CASCADE,
  PRIMARY KEY (club_id, tag_id)
);

CREATE TABLE club_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role club_member_role NOT NULL DEFAULT 'member',
  status club_member_status NOT NULL DEFAULT 'active',
  joined_at timestamptz NOT NULL DEFAULT now(),
  left_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (club_id, user_id)
);

CREATE TABLE events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  title text NOT NULL,
  slug text NOT NULL,
  description text,
  event_type text NOT NULL,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz,
  timezone text NOT NULL DEFAULT 'Asia/Riyadh',
  location_name text,
  address text,
  city text,
  country text DEFAULT 'Saudi Arabia',
  lat numeric(9,6),
  lng numeric(9,6),
  capacity integer,
  registered_count integer NOT NULL DEFAULT 0,
  waitlist_count integer NOT NULL DEFAULT 0,
  price_amount numeric(10,2) NOT NULL DEFAULT 0,
  currency char(3) NOT NULL DEFAULT 'SAR',
  status event_status NOT NULL DEFAULT 'draft',
  requires_approval boolean NOT NULL DEFAULT false,
  cover_image_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  UNIQUE (club_id, slug),
  CONSTRAINT events_title_len CHECK (char_length(title) BETWEEN 3 AND 200),
  CONSTRAINT events_description_len CHECK (description IS NULL OR char_length(description) <= 5000),
  CONSTRAINT events_end_after_start CHECK (ends_at IS NULL OR ends_at > starts_at),
  CONSTRAINT events_lat_valid CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
  CONSTRAINT events_lng_valid CHECK (lng IS NULL OR lng BETWEEN -180 AND 180),
  CONSTRAINT events_capacity_positive CHECK (capacity IS NULL OR capacity > 0),
  CONSTRAINT events_counts_nonnegative CHECK (registered_count >= 0 AND waitlist_count >= 0),
  CONSTRAINT events_price_nonnegative CHECK (price_amount >= 0)
);

CREATE TABLE event_registrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status event_registration_status NOT NULL DEFAULT 'confirmed',
  waitlist_position integer,
  note text,
  registered_at timestamptz NOT NULL DEFAULT now(),
  confirmed_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id, user_id),
  CONSTRAINT event_registrations_waitlist_position_positive CHECK (
    waitlist_position IS NULL OR waitlist_position > 0
  )
);

CREATE TABLE saved_events (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, event_id)
);

CREATE TABLE notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind notification_kind NOT NULL DEFAULT 'system',
  title text NOT NULL,
  body text NOT NULL,
  entity_type text,
  entity_id uuid,
  read_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT notifications_title_len CHECK (char_length(title) BETWEEN 1 AND 160),
  CONSTRAINT notifications_body_len CHECK (char_length(body) BETWEEN 1 AND 1000)
);

CREATE TABLE media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  uploaded_by uuid REFERENCES users(id) ON DELETE SET NULL,
  owner_type media_owner_type NOT NULL,
  owner_id uuid NOT NULL,
  url text NOT NULL,
  storage_key text NOT NULL UNIQUE,
  mime_type text NOT NULL,
  size_bytes bigint,
  alt_text text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT media_assets_size_positive CHECK (size_bytes IS NULL OR size_bytes > 0)
);

CREATE TABLE audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid REFERENCES users(id) ON DELETE SET NULL,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE search_embeddings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type embedding_entity_type NOT NULL,
  entity_id uuid NOT NULL,
  -- Temporary local setup uses a numeric array because pgvector is not installed yet.
  -- After pgvector is installed, migrate this to: embedding vector(1536) NOT NULL
  embedding double precision[] NOT NULL,
  content_text text NOT NULL,
  content_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (entity_type, entity_id)
);

CREATE TABLE recommendation_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  source text NOT NULL DEFAULT 'hybrid',
  score numeric(6,5),
  action recommendation_action NOT NULL DEFAULT 'impression',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT recommendation_events_score_range CHECK (score IS NULL OR score BETWEEN 0 AND 1)
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organizer_requests_set_updated_at
BEFORE UPDATE ON organizer_requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER user_preferences_set_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER clubs_set_updated_at
BEFORE UPDATE ON clubs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER club_members_set_updated_at
BEFORE UPDATE ON club_members
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER events_set_updated_at
BEFORE UPDATE ON events
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER event_registrations_set_updated_at
BEFORE UPDATE ON event_registrations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER search_embeddings_set_updated_at
BEFORE UPDATE ON search_embeddings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION refresh_club_member_count(p_club_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE clubs
  SET member_count = (
    SELECT count(*)::integer
    FROM club_members
    WHERE club_id = p_club_id
      AND status = 'active'
  )
  WHERE id = p_club_id;
END;
$$;

CREATE OR REPLACE FUNCTION sync_club_member_count()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') THEN
    PERFORM refresh_club_member_count(OLD.club_id);
  END IF;

  IF TG_OP IN ('INSERT', 'UPDATE') THEN
    PERFORM refresh_club_member_count(NEW.club_id);
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER club_members_sync_count
AFTER INSERT OR UPDATE OR DELETE ON club_members
FOR EACH ROW EXECUTE FUNCTION sync_club_member_count();

CREATE OR REPLACE FUNCTION refresh_event_registration_counts(p_event_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE events
  SET
    registered_count = (
      SELECT count(*)::integer
      FROM event_registrations
      WHERE event_id = p_event_id
        AND status = 'confirmed'
    ),
    waitlist_count = (
      SELECT count(*)::integer
      FROM event_registrations
      WHERE event_id = p_event_id
        AND status = 'waitlisted'
    )
  WHERE id = p_event_id;
END;
$$;

CREATE OR REPLACE FUNCTION sync_event_registration_counts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') THEN
    PERFORM refresh_event_registration_counts(OLD.event_id);
  END IF;

  IF TG_OP IN ('INSERT', 'UPDATE') THEN
    PERFORM refresh_event_registration_counts(NEW.event_id);
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER event_registrations_sync_counts
AFTER INSERT OR UPDATE OR DELETE ON event_registrations
FOR EACH ROW EXECUTE FUNCTION sync_event_registration_counts();

CREATE OR REPLACE FUNCTION auto_waitlist_registration()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  event_capacity integer;
  current_confirmed integer;
  next_position integer;
BEGIN
  SELECT capacity INTO event_capacity
  FROM events
  WHERE id = NEW.event_id;

  IF NEW.status = 'confirmed' AND event_capacity IS NOT NULL THEN
    SELECT count(*)::integer INTO current_confirmed
    FROM event_registrations
    WHERE event_id = NEW.event_id
      AND status = 'confirmed'
      AND id IS DISTINCT FROM NEW.id;

    IF current_confirmed >= event_capacity THEN
      NEW.status = 'waitlisted';
    END IF;
  END IF;

  IF NEW.status = 'waitlisted' AND NEW.waitlist_position IS NULL THEN
    SELECT COALESCE(max(waitlist_position), 0) + 1 INTO next_position
    FROM event_registrations
    WHERE event_id = NEW.event_id
      AND status = 'waitlisted';

    NEW.waitlist_position = next_position;
  END IF;

  IF NEW.status = 'confirmed' AND NEW.confirmed_at IS NULL THEN
    NEW.confirmed_at = now();
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER event_registrations_10_auto_waitlist
BEFORE INSERT OR UPDATE OF status ON event_registrations
FOR EACH ROW EXECUTE FUNCTION auto_waitlist_registration();

CREATE OR REPLACE FUNCTION prevent_over_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  event_capacity integer;
  current_confirmed integer;
BEGIN
  IF NEW.status <> 'confirmed' THEN
    RETURN NEW;
  END IF;

  SELECT capacity INTO event_capacity
  FROM events
  WHERE id = NEW.event_id;

  IF event_capacity IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT count(*)::integer INTO current_confirmed
  FROM event_registrations
  WHERE event_id = NEW.event_id
    AND status = 'confirmed'
    AND id IS DISTINCT FROM NEW.id;

  IF current_confirmed >= event_capacity THEN
    RAISE EXCEPTION 'Event % is already at capacity', NEW.event_id
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER event_registrations_20_prevent_over_capacity
BEFORE INSERT OR UPDATE OF status ON event_registrations
FOR EACH ROW EXECUTE FUNCTION prevent_over_capacity();

CREATE OR REPLACE FUNCTION promote_waitlist(p_event_id uuid)
RETURNS event_registrations
LANGUAGE plpgsql
AS $$
DECLARE
  target_event events%ROWTYPE;
  promoted event_registrations%ROWTYPE;
  current_confirmed integer;
BEGIN
  SELECT * INTO target_event
  FROM events
  WHERE id = p_event_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Event not found: %', p_event_id;
  END IF;

  IF target_event.capacity IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT count(*)::integer INTO current_confirmed
  FROM event_registrations
  WHERE event_id = p_event_id
    AND status = 'confirmed';

  IF current_confirmed >= target_event.capacity THEN
    RETURN NULL;
  END IF;

  SELECT * INTO promoted
  FROM event_registrations
  WHERE event_id = p_event_id
    AND status = 'waitlisted'
  ORDER BY waitlist_position ASC, registered_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  UPDATE event_registrations
  SET status = 'confirmed',
      confirmed_at = now(),
      waitlist_position = NULL
  WHERE id = promoted.id
  RETURNING * INTO promoted;

  INSERT INTO notifications (user_id, kind, title, body, entity_type, entity_id)
  VALUES (
    promoted.user_id,
    'waitlist',
    'You are in',
    'A spot opened up and your event registration was confirmed.',
    'event',
    p_event_id
  );

  RETURN promoted;
END;
$$;

CREATE OR REPLACE FUNCTION register_for_event(p_user_id uuid, p_event_id uuid)
RETURNS event_registrations
LANGUAGE plpgsql
AS $$
DECLARE
  target_event events%ROWTYPE;
  existing_registration event_registrations%ROWTYPE;
  new_status event_registration_status;
  created_registration event_registrations%ROWTYPE;
BEGIN
  SELECT * INTO target_event
  FROM events
  WHERE id = p_event_id
    AND deleted_at IS NULL
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Event not found: %', p_event_id;
  END IF;

  IF target_event.status <> 'published' THEN
    RAISE EXCEPTION 'Event is not open for registration';
  END IF;

  SELECT * INTO existing_registration
  FROM event_registrations
  WHERE event_id = p_event_id
    AND user_id = p_user_id;

  IF FOUND AND existing_registration.status NOT IN ('cancelled', 'rejected') THEN
    RETURN existing_registration;
  END IF;

  IF target_event.requires_approval THEN
    new_status = 'pending';
  ELSIF target_event.capacity IS NULL OR target_event.registered_count < target_event.capacity THEN
    new_status = 'confirmed';
  ELSE
    new_status = 'waitlisted';
  END IF;

  INSERT INTO event_registrations (event_id, user_id, status)
  VALUES (p_event_id, p_user_id, new_status)
  ON CONFLICT (event_id, user_id)
  DO UPDATE SET
    status = EXCLUDED.status,
    registered_at = now(),
    cancelled_at = NULL,
    note = NULL
  RETURNING * INTO created_registration;

  RETURN created_registration;
END;
$$;

CREATE OR REPLACE FUNCTION cancel_event_registration(p_user_id uuid, p_event_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  old_status event_registration_status;
BEGIN
  PERFORM 1 FROM events WHERE id = p_event_id FOR UPDATE;

  UPDATE event_registrations
  SET status = 'cancelled',
      cancelled_at = now(),
      waitlist_position = NULL
  WHERE event_id = p_event_id
    AND user_id = p_user_id
    AND status IN ('pending', 'confirmed', 'waitlisted')
  RETURNING status INTO old_status;

  IF old_status = 'confirmed' THEN
    PERFORM promote_waitlist(p_event_id);
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION join_club(p_user_id uuid, p_club_id uuid)
RETURNS club_members
LANGUAGE plpgsql
AS $$
DECLARE
  target_club clubs%ROWTYPE;
  join_status club_member_status;
  membership club_members%ROWTYPE;
BEGIN
  SELECT * INTO target_club
  FROM clubs
  WHERE id = p_club_id
    AND deleted_at IS NULL
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Club not found: %', p_club_id;
  END IF;

  IF target_club.status <> 'published' THEN
    RAISE EXCEPTION 'Club is not open for joining';
  END IF;

  join_status = CASE WHEN target_club.visibility = 'public' THEN 'active' ELSE 'pending' END;

  INSERT INTO club_members (club_id, user_id, role, status)
  VALUES (p_club_id, p_user_id, 'member', join_status)
  ON CONFLICT (club_id, user_id)
  DO UPDATE SET
    status = EXCLUDED.status,
    left_at = NULL
  RETURNING * INTO membership;

  RETURN membership;
END;
$$;

CREATE OR REPLACE FUNCTION leave_club(p_user_id uuid, p_club_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE club_members
  SET status = 'left',
      left_at = now()
  WHERE club_id = p_club_id
    AND user_id = p_user_id
    AND role <> 'owner';
END;
$$;

CREATE OR REPLACE FUNCTION audit_row_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO audit_logs (action, entity_type, entity_id, metadata)
  VALUES (
    lower(TG_OP),
    TG_ARGV[0],
    COALESCE(NEW.id, OLD.id),
    jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW))
  );

  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER clubs_audit_changes
AFTER UPDATE OR DELETE ON clubs
FOR EACH ROW EXECUTE FUNCTION audit_row_change('club');

CREATE TRIGGER events_audit_changes
AFTER UPDATE OR DELETE ON events
FOR EACH ROW EXECUTE FUNCTION audit_row_change('event');

CREATE VIEW public_club_cards AS
SELECT
  c.id,
  c.name,
  c.slug,
  c.description,
  c.logo_url,
  c.cover_image_url,
  c.city,
  c.country,
  c.member_count,
  cc.name AS category_name,
  c.created_at
FROM clubs c
LEFT JOIN club_categories cc ON cc.id = c.category_id
WHERE c.status = 'published'
  AND c.visibility = 'public'
  AND c.deleted_at IS NULL;

CREATE VIEW public_event_cards AS
SELECT
  e.id,
  e.club_id,
  c.name AS club_name,
  e.title,
  e.slug,
  e.description,
  e.event_type,
  e.starts_at,
  e.ends_at,
  e.city,
  e.country,
  e.location_name,
  e.capacity,
  e.registered_count,
  e.waitlist_count,
  e.price_amount,
  e.currency,
  e.cover_image_url,
  cc.name AS category_name
FROM events e
JOIN clubs c ON c.id = e.club_id
LEFT JOIN club_categories cc ON cc.id = c.category_id
WHERE e.status = 'published'
  AND e.deleted_at IS NULL
  AND c.deleted_at IS NULL;

CREATE VIEW event_detail_view AS
SELECT
  e.*,
  c.name AS club_name,
  c.slug AS club_slug,
  c.logo_url AS club_logo_url,
  u.display_name AS organizer_name,
  u.avatar_url AS organizer_avatar_url,
  (e.capacity IS NOT NULL AND e.registered_count >= e.capacity) AS is_full
FROM events e
JOIN clubs c ON c.id = e.club_id
JOIN users u ON u.id = e.created_by
WHERE e.deleted_at IS NULL;

CREATE VIEW club_detail_view AS
SELECT
  c.*,
  cc.name AS category_name,
  u.display_name AS owner_name,
  u.avatar_url AS owner_avatar_url
FROM clubs c
LEFT JOIN club_categories cc ON cc.id = c.category_id
JOIN users u ON u.id = c.owner_id
WHERE c.deleted_at IS NULL;

CREATE VIEW organizer_dashboard_view AS
SELECT
  c.owner_id,
  c.id AS club_id,
  c.name AS club_name,
  count(DISTINCT e.id) AS total_events,
  count(DISTINCT er.id) FILTER (WHERE er.status = 'confirmed') AS confirmed_registrations,
  count(DISTINCT cm.id) FILTER (WHERE cm.status = 'active') AS active_members
FROM clubs c
LEFT JOIN events e ON e.club_id = c.id AND e.deleted_at IS NULL
LEFT JOIN event_registrations er ON er.event_id = e.id
LEFT JOIN club_members cm ON cm.club_id = c.id
WHERE c.deleted_at IS NULL
GROUP BY c.owner_id, c.id, c.name;

CREATE VIEW user_registered_events_view AS
SELECT
  er.user_id,
  er.status AS registration_status,
  er.registered_at,
  e.*
FROM event_registrations er
JOIN events e ON e.id = er.event_id
WHERE er.status IN ('pending', 'confirmed', 'waitlisted')
  AND e.deleted_at IS NULL;

CREATE VIEW event_capacity_view AS
SELECT
  id AS event_id,
  capacity,
  registered_count,
  waitlist_count,
  CASE
    WHEN capacity IS NULL THEN NULL
    ELSE greatest(capacity - registered_count, 0)
  END AS spots_left,
  (capacity IS NOT NULL AND registered_count >= capacity) AS is_full
FROM events
WHERE deleted_at IS NULL;

CREATE VIEW search_index_view AS
SELECT
  'club'::text AS entity_type,
  c.id AS entity_id,
  c.name AS title,
  c.description AS body,
  c.city,
  c.country,
  c.created_at
FROM clubs c
WHERE c.status = 'published'
  AND c.visibility = 'public'
  AND c.deleted_at IS NULL
UNION ALL
SELECT
  'event'::text AS entity_type,
  e.id AS entity_id,
  e.title,
  e.description AS body,
  e.city,
  e.country,
  e.created_at
FROM events e
WHERE e.status = 'published'
  AND e.deleted_at IS NULL;

CREATE INDEX users_email_idx ON users (email);
CREATE INDEX users_clerk_user_id_idx ON users (clerk_user_id);
CREATE INDEX users_deleted_at_idx ON users (deleted_at);
CREATE INDEX organizer_requests_status_idx ON organizer_requests (status, created_at DESC);
CREATE INDEX organizer_requests_user_status_idx ON organizer_requests (user_id, status);

CREATE INDEX clubs_owner_id_idx ON clubs (owner_id);
CREATE INDEX clubs_category_id_idx ON clubs (category_id);
CREATE INDEX clubs_status_visibility_idx ON clubs (status, visibility);
CREATE INDEX clubs_city_idx ON clubs (city);
CREATE INDEX clubs_name_trgm_idx ON clubs USING gin (name gin_trgm_ops);
CREATE INDEX clubs_description_trgm_idx ON clubs USING gin (description gin_trgm_ops);

CREATE INDEX club_members_user_id_idx ON club_members (user_id);
CREATE INDEX club_members_club_status_idx ON club_members (club_id, status);

CREATE INDEX events_club_id_idx ON events (club_id);
CREATE INDEX events_created_by_idx ON events (created_by);
CREATE INDEX events_status_starts_at_idx ON events (status, starts_at);
CREATE INDEX events_city_event_type_idx ON events (city, event_type);
CREATE INDEX events_title_trgm_idx ON events USING gin (title gin_trgm_ops);
CREATE INDEX events_description_trgm_idx ON events USING gin (description gin_trgm_ops);

CREATE INDEX event_registrations_user_id_idx ON event_registrations (user_id);
CREATE INDEX event_registrations_event_status_idx ON event_registrations (event_id, status);
CREATE INDEX event_registrations_waitlist_order_idx
  ON event_registrations (event_id, waitlist_position, registered_at)
  WHERE status = 'waitlisted';

CREATE INDEX saved_events_event_id_idx ON saved_events (event_id);
CREATE INDEX notifications_user_unread_idx ON notifications (user_id, created_at DESC) WHERE read_at IS NULL;
CREATE INDEX media_assets_owner_idx ON media_assets (owner_type, owner_id);
CREATE INDEX audit_logs_entity_idx ON audit_logs (entity_type, entity_id);
CREATE INDEX audit_logs_created_at_idx ON audit_logs (created_at DESC);
CREATE INDEX search_embeddings_entity_idx ON search_embeddings (entity_type, entity_id);
-- Enable this later after migrating search_embeddings.embedding to vector(1536):
-- CREATE INDEX search_embeddings_vector_idx ON search_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX recommendation_events_user_created_idx ON recommendation_events (user_id, created_at DESC);

INSERT INTO club_categories (name, slug, description)
VALUES
  ('Outdoors', 'outdoors', 'Hiking, camping, trips, and nature experiences'),
  ('Sports', 'sports', 'Running, climbing, fitness, and active communities'),
  ('Culture', 'culture', 'Arts, language, heritage, and local culture'),
  ('Food', 'food', 'Supper clubs, food crawls, and cooking experiences'),
  ('Music', 'music', 'Live music, jam sessions, and performance communities'),
  ('Wellness', 'wellness', 'Yoga, meditation, mindfulness, and health'),
  ('Technology', 'technology', 'Tech clubs, makers, AI, and startup groups')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO club_tags (name, slug)
VALUES
  ('Beginner friendly', 'beginner-friendly'),
  ('Women friendly', 'women-friendly'),
  ('Free', 'free'),
  ('Weekend', 'weekend'),
  ('Student friendly', 'student-friendly'),
  ('Outdoor', 'outdoor'),
  ('Networking', 'networking'),
  ('Creative', 'creative')
ON CONFLICT (slug) DO NOTHING;

COMMIT;

