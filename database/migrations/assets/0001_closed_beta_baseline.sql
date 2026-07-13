-- Talaqi closed-beta bootstrap schema.
-- Target: PostgreSQL 18.4 or newer in the PostgreSQL 18 release line.
-- Run once on an empty database. Future changes must use Alembic migrations.
-- This script intentionally creates no login roles and stores no credentials.

BEGIN;

CREATE SCHEMA talaqi;
REVOKE ALL ON SCHEMA talaqi FROM PUBLIC;
SET LOCAL search_path = talaqi, public;

CREATE TYPE user_status AS ENUM ('active', 'suspended', 'deleted');
CREATE TYPE auth_token_kind AS ENUM ('email_verification', 'password_reset');
CREATE TYPE club_membership_policy AS ENUM ('open', 'approval_required');
CREATE TYPE club_role AS ENUM ('owner', 'admin', 'member');
CREATE TYPE club_status AS ENUM ('draft', 'published', 'unpublished', 'suspended', 'closed');
CREATE TYPE join_request_status AS ENUM ('pending', 'approved', 'rejected', 'cancelled');
CREATE TYPE event_ownership_type AS ENUM ('club', 'independent');
CREATE TYPE event_visibility AS ENUM ('public', 'private_link');
CREATE TYPE event_status AS ENUM ('draft', 'published', 'cancelled', 'completed', 'suspended');
CREATE TYPE registration_method AS ENUM ('free', 'cash_organizer_confirmed');
CREATE TYPE registration_state AS ENUM ('confirmed', 'cash_pending', 'waitlisted', 'cancelled', 'expired');
CREATE TYPE media_status AS ENUM ('pending', 'verified', 'quarantined', 'deleted');
CREATE TYPE notification_channel AS ENUM ('in_app', 'email');
CREATE TYPE delivery_status AS ENUM ('pending', 'processing', 'delivered', 'retryable_failed', 'permanent_failed');
CREATE TYPE moderation_target_type AS ENUM ('user', 'club', 'event');
CREATE TYPE moderation_case_status AS ENUM ('open', 'investigating', 'actioned', 'dismissed');
CREATE TYPE moderation_priority AS ENUM ('standard', 'high', 'emergency');
CREATE TYPE moderation_action AS ENUM ('suspend', 'unpublish', 'restore', 'restrict');

CREATE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;

CREATE FUNCTION reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

CREATE TABLE schema_revisions (
    revision text PRIMARY KEY,
    description text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO schema_revisions (revision, description)
VALUES ('2026-07-11-bootstrap', 'Talaqi MVP closed-beta baseline');

CREATE TABLE countries (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    code char(2) NOT NULL UNIQUE CHECK (code = upper(code)),
    name_key text NOT NULL UNIQUE,
    default_locale text NOT NULL CHECK (default_locale IN ('en', 'tr', 'fr', 'ar')),
    default_currency char(3) NOT NULL CHECK (default_currency = upper(default_currency)),
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TRIGGER countries_set_updated_at
BEFORE UPDATE ON countries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE cities (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    country_id uuid NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
    slug text NOT NULL CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    name_key text NOT NULL,
    time_zone text NOT NULL CHECK (time_zone ~ '^(UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+)$'),
    latitude numeric(9,6),
    longitude numeric(9,6),
    beta_enabled boolean NOT NULL DEFAULT false,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_cities_country_slug UNIQUE (country_id, slug),
    CONSTRAINT uq_cities_id_country UNIQUE (id, country_id),
    CONSTRAINT ck_cities_coordinates_pair CHECK ((latitude IS NULL) = (longitude IS NULL)),
    CONSTRAINT ck_cities_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_cities_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE INDEX ix_cities_country_enabled ON cities (country_id, enabled, slug);
CREATE TRIGGER cities_set_updated_at
BEFORE UPDATE ON cities
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE categories (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    name_key text NOT NULL UNIQUE,
    icon_key text NOT NULL,
    sort_order integer NOT NULL DEFAULT 0,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_categories_discovery ON categories (enabled, sort_order, slug);
CREATE TRIGGER categories_set_updated_at
BEFORE UPDATE ON categories
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE regional_policies (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    country_id uuid NOT NULL UNIQUE REFERENCES countries(id) ON DELETE RESTRICT,
    allowed_registration_methods registration_method[] NOT NULL,
    cash_expiry_default_minutes integer NOT NULL,
    cash_expiry_min_minutes integer NOT NULL,
    cash_expiry_max_minutes integer NOT NULL,
    cancellation_default_minutes integer NOT NULL,
    cancellation_min_minutes integer NOT NULL,
    cancellation_max_minutes integer NOT NULL,
    default_club_ownership_limit integer NOT NULL DEFAULT 1,
    default_active_independent_event_limit integer NOT NULL DEFAULT 3,
    exact_venue_public_by_default boolean NOT NULL DEFAULT false,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_regional_cash_bounds CHECK (
        cash_expiry_min_minutes >= 0
        AND cash_expiry_min_minutes <= cash_expiry_default_minutes
        AND cash_expiry_default_minutes <= cash_expiry_max_minutes
    ),
    CONSTRAINT ck_regional_cancellation_bounds CHECK (
        cancellation_min_minutes >= 0
        AND cancellation_min_minutes <= cancellation_default_minutes
        AND cancellation_default_minutes <= cancellation_max_minutes
    ),
    CONSTRAINT ck_regional_positive_limits CHECK (
        default_club_ownership_limit >= 0
        AND default_active_independent_event_limit >= 0
    ),
    CONSTRAINT ck_regional_methods_nonempty CHECK (cardinality(allowed_registration_methods) > 0)
);

CREATE TRIGGER regional_policies_set_updated_at
BEFORE UPDATE ON regional_policies
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    email text NOT NULL CHECK (length(email) BETWEEN 3 AND 320 AND email = lower(btrim(email))),
    password_hash text NOT NULL CHECK (password_hash LIKE '$argon2id$%'),
    status user_status NOT NULL DEFAULT 'active',
    email_verified_at timestamptz,
    terms_version text NOT NULL,
    privacy_version text NOT NULL,
    age_attested_at timestamptz NOT NULL,
    organizer_rules_version text,
    community_rules_version text,
    is_platform_admin boolean NOT NULL DEFAULT false,
    failed_login_count integer NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until timestamptz,
    suspended_at timestamptz,
    suspension_reason text,
    deletion_requested_at timestamptz,
    anonymized_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_users_suspension_shape CHECK (
        (status = 'suspended' AND suspended_at IS NOT NULL AND suspension_reason IS NOT NULL)
        OR status <> 'suspended'
    ),
    CONSTRAINT ck_users_deleted_shape CHECK (status <> 'deleted' OR anonymized_at IS NOT NULL)
);

CREATE UNIQUE INDEX uq_users_email_normalized ON users (lower(email));
CREATE INDEX ix_users_status_created ON users (status, created_at DESC);
CREATE INDEX ix_users_pending_deletion ON users (deletion_requested_at)
WHERE deletion_requested_at IS NOT NULL AND anonymized_at IS NULL;
CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE profiles (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    username text NOT NULL CHECK (username ~ '^[a-z0-9_]{3,30}$'),
    display_name text NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 80),
    country_id uuid NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
    city_id uuid NOT NULL,
    locale text NOT NULL CHECK (locale IN ('en', 'tr', 'fr', 'ar')),
    time_zone text NOT NULL CHECK (time_zone ~ '^(UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+)$'),
    preferred_currency char(3) NOT NULL CHECK (preferred_currency = upper(preferred_currency)),
    avatar_media_id uuid,
    notify_security_email boolean NOT NULL DEFAULT true CHECK (notify_security_email),
    notify_event_email boolean NOT NULL DEFAULT true,
    notify_community_email boolean NOT NULL DEFAULT true,
    profile_completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT fk_profiles_city_country FOREIGN KEY (city_id, country_id)
        REFERENCES cities(id, country_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_profiles_username_normalized ON profiles (lower(username));
CREATE INDEX ix_profiles_region ON profiles (country_id, city_id);
CREATE TRIGGER profiles_set_updated_at
BEFORE UPDATE ON profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE sessions (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id uuid NOT NULL DEFAULT uuidv7(),
    refresh_token_hash bytea NOT NULL UNIQUE CHECK (octet_length(refresh_token_hash) >= 32),
    csrf_secret_hash bytea NOT NULL CHECK (octet_length(csrf_secret_hash) >= 32),
    user_agent_hash bytea,
    ip_prefix inet,
    expires_at timestamptz NOT NULL,
    last_used_at timestamptz,
    rotated_at timestamptz,
    revoked_at timestamptz,
    revoke_reason text,
    replaced_by_session_id uuid REFERENCES sessions(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_sessions_revoke_shape CHECK ((revoked_at IS NULL) = (revoke_reason IS NULL))
);

CREATE INDEX ix_sessions_user_active ON sessions (user_id, expires_at DESC) WHERE revoked_at IS NULL;
CREATE INDEX ix_sessions_family ON sessions (family_id, created_at);
CREATE INDEX ix_sessions_retention ON sessions (revoked_at) WHERE revoked_at IS NOT NULL;

CREATE TABLE auth_tokens (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind auth_token_kind NOT NULL,
    token_hash bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) >= 32),
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_auth_tokens_user_kind ON auth_tokens (user_id, kind, created_at DESC);
CREATE INDEX ix_auth_tokens_cleanup ON auth_tokens (expires_at, used_at);

CREATE TABLE user_mfa_factors (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    factor_type text NOT NULL CHECK (factor_type IN ('totp', 'webauthn', 'recovery_code')),
    secret_ciphertext bytea NOT NULL,
    label text,
    verified_at timestamptz,
    disabled_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_user_mfa_active ON user_mfa_factors (user_id, factor_type)
WHERE verified_at IS NOT NULL AND disabled_at IS NULL;

CREATE TABLE media_assets (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status media_status NOT NULL DEFAULT 'pending',
    storage_key text NOT NULL UNIQUE CHECK (storage_key !~ '(^|/)\.\.(/|$)'),
    original_filename text NOT NULL CHECK (original_filename !~ '[/\\]'),
    content_type text NOT NULL CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
    byte_size bigint NOT NULL CHECK (byte_size BETWEEN 1 AND 10485760),
    width integer CHECK (width IS NULL OR width BETWEEN 1 AND 12000),
    height integer CHECK (height IS NULL OR height BETWEEN 1 AND 12000),
    sha256 bytea CHECK (sha256 IS NULL OR octet_length(sha256) = 32),
    verified_at timestamptz,
    quarantine_reason text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_media_verified_shape CHECK (status <> 'verified' OR (verified_at IS NOT NULL AND sha256 IS NOT NULL)),
    CONSTRAINT ck_media_quarantine_shape CHECK (status <> 'quarantined' OR quarantine_reason IS NOT NULL)
);

ALTER TABLE profiles
ADD CONSTRAINT fk_profiles_avatar_media
FOREIGN KEY (avatar_media_id) REFERENCES media_assets(id) ON DELETE SET NULL;

CREATE INDEX ix_media_owner_status ON media_assets (owner_user_id, status, created_at DESC);
CREATE INDEX ix_media_pending_cleanup ON media_assets (created_at) WHERE status = 'pending';
CREATE TRIGGER media_assets_set_updated_at
BEFORE UPDATE ON media_assets
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE clubs (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    slug text NOT NULL CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 2 AND 120),
    description text,
    category_id uuid REFERENCES categories(id) ON DELETE RESTRICT,
    country_id uuid REFERENCES countries(id) ON DELETE RESTRICT,
    city_id uuid,
    membership_policy club_membership_policy NOT NULL DEFAULT 'open',
    status club_status NOT NULL DEFAULT 'draft',
    logo_media_id uuid REFERENCES media_assets(id) ON DELETE SET NULL,
    cover_media_id uuid REFERENCES media_assets(id) ON DELETE SET NULL,
    social_links jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(social_links) = 'object'),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    published_at timestamptz,
    suspended_at timestamptz,
    suspension_reason text,
    closed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_clubs_slug UNIQUE (slug),
    CONSTRAINT ck_clubs_publication_fields CHECK (
        status NOT IN ('published', 'unpublished', 'suspended')
        OR (description IS NOT NULL AND length(btrim(description)) > 0
            AND category_id IS NOT NULL AND country_id IS NOT NULL AND city_id IS NOT NULL)
    ),
    CONSTRAINT ck_clubs_published_at CHECK (status <> 'published' OR published_at IS NOT NULL),
    CONSTRAINT ck_clubs_suspension_shape CHECK (
        (status = 'suspended' AND suspended_at IS NOT NULL AND suspension_reason IS NOT NULL)
        OR status <> 'suspended'
    ),
    CONSTRAINT ck_clubs_closed_at CHECK (status <> 'closed' OR closed_at IS NOT NULL),
    CONSTRAINT fk_clubs_city_country FOREIGN KEY (city_id, country_id)
        REFERENCES cities(id, country_id) ON DELETE RESTRICT
);

CREATE INDEX ix_clubs_discovery ON clubs (country_id, city_id, category_id, created_at DESC)
WHERE status = 'published';
CREATE INDEX ix_clubs_owner ON clubs (owner_user_id, status, created_at DESC);
CREATE INDEX ix_clubs_search ON clubs USING gin (to_tsvector('simple', name || ' ' || coalesce(description, '')))
WHERE status = 'published';
CREATE TRIGGER clubs_set_updated_at
BEFORE UPDATE ON clubs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE club_memberships (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    role club_role NOT NULL DEFAULT 'member',
    joined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_club_memberships_member UNIQUE (club_id, user_id)
);

CREATE UNIQUE INDEX uq_club_memberships_single_owner ON club_memberships (club_id)
WHERE role = 'owner';
CREATE INDEX ix_club_memberships_user ON club_memberships (user_id, joined_at DESC);
CREATE INDEX ix_club_memberships_managers ON club_memberships (club_id, role)
WHERE role IN ('owner', 'admin');
CREATE TRIGGER club_memberships_set_updated_at
BEFORE UPDATE ON club_memberships
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE club_join_requests (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status join_request_status NOT NULL DEFAULT 'pending',
    message text CHECK (message IS NULL OR length(message) <= 500),
    decided_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    decision_reason text,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_join_request_decision_shape CHECK (
        (status IN ('approved', 'rejected') AND decided_by_user_id IS NOT NULL AND decided_at IS NOT NULL)
        OR status IN ('pending', 'cancelled')
    )
);

CREATE UNIQUE INDEX uq_club_join_requests_pending ON club_join_requests (club_id, user_id)
WHERE status = 'pending';
CREATE INDEX ix_club_join_requests_queue ON club_join_requests (club_id, status, created_at);
CREATE TRIGGER club_join_requests_set_updated_at
BEFORE UPDATE ON club_join_requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE events (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    ownership_type event_ownership_type NOT NULL,
    club_id uuid REFERENCES clubs(id) ON DELETE RESTRICT,
    owner_user_id uuid REFERENCES users(id) ON DELETE RESTRICT,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 2 AND 160),
    description text NOT NULL DEFAULT '' CHECK (length(description) <= 20000),
    category_id uuid REFERENCES categories(id) ON DELETE RESTRICT,
    country_id uuid REFERENCES countries(id) ON DELETE RESTRICT,
    city_id uuid,
    start_at timestamptz,
    end_at timestamptz,
    time_zone text CHECK (time_zone IS NULL OR time_zone ~ '^(UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+)$'),
    capacity integer CHECK (capacity IS NULL OR capacity > 0),
    visibility event_visibility NOT NULL DEFAULT 'public',
    status event_status NOT NULL DEFAULT 'draft',
    registration_method registration_method,
    cash_expiry_minutes integer CHECK (cash_expiry_minutes IS NULL OR cash_expiry_minutes >= 0),
    cancellation_cutoff_minutes integer CHECK (cancellation_cutoff_minutes IS NULL OR cancellation_cutoff_minutes >= 0),
    district text CHECK (district IS NULL OR length(district) <= 120),
    public_meeting_area text CHECK (public_meeting_area IS NULL OR length(public_meeting_area) <= 300),
    exact_address text CHECK (exact_address IS NULL OR length(exact_address) <= 500),
    latitude numeric(9,6),
    longitude numeric(9,6),
    exact_venue_is_public boolean NOT NULL DEFAULT false,
    cover_media_id uuid REFERENCES media_assets(id) ON DELETE SET NULL,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    published_at timestamptz,
    cancelled_at timestamptz,
    completed_at timestamptz,
    suspended_at timestamptz,
    suspension_reason text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_events_owner_shape CHECK (
        (ownership_type = 'club' AND club_id IS NOT NULL AND owner_user_id IS NULL)
        OR (ownership_type = 'independent' AND club_id IS NULL AND owner_user_id IS NOT NULL)
    ),
    CONSTRAINT ck_events_coordinates_pair CHECK ((latitude IS NULL) = (longitude IS NULL)),
    CONSTRAINT ck_events_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_events_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    CONSTRAINT ck_events_schedule CHECK (start_at IS NULL OR end_at IS NULL OR end_at > start_at),
    CONSTRAINT ck_events_published_fields CHECK (
        status NOT IN ('published', 'cancelled', 'completed', 'suspended')
        OR (length(btrim(description)) > 0
            AND category_id IS NOT NULL AND country_id IS NOT NULL AND city_id IS NOT NULL
            AND start_at IS NOT NULL AND end_at IS NOT NULL AND time_zone IS NOT NULL
            AND capacity IS NOT NULL AND registration_method IS NOT NULL
            AND cancellation_cutoff_minutes IS NOT NULL)
    ),
    CONSTRAINT ck_events_cash_expiry CHECK (
        registration_method <> 'cash_organizer_confirmed' OR cash_expiry_minutes IS NOT NULL
    ),
    CONSTRAINT ck_events_published_at CHECK (status <> 'published' OR published_at IS NOT NULL),
    CONSTRAINT ck_events_cancelled_at CHECK (status <> 'cancelled' OR cancelled_at IS NOT NULL),
    CONSTRAINT ck_events_completed_at CHECK (status <> 'completed' OR completed_at IS NOT NULL),
    CONSTRAINT ck_events_suspension_shape CHECK (
        (status = 'suspended' AND suspended_at IS NOT NULL AND suspension_reason IS NOT NULL)
        OR status <> 'suspended'
    ),
    CONSTRAINT fk_events_city_country FOREIGN KEY (city_id, country_id)
        REFERENCES cities(id, country_id) ON DELETE RESTRICT
);

CREATE INDEX ix_events_public_discovery ON events (country_id, city_id, category_id, start_at, id)
WHERE status = 'published' AND visibility = 'public';
CREATE INDEX ix_events_club ON events (club_id, start_at DESC) WHERE club_id IS NOT NULL;
CREATE INDEX ix_events_independent_owner ON events (owner_user_id, status, start_at DESC) WHERE owner_user_id IS NOT NULL;
CREATE INDEX ix_events_search ON events USING gin (to_tsvector('simple', title || ' ' || description))
WHERE status = 'published' AND visibility = 'public';
CREATE TRIGGER events_set_updated_at
BEFORE UPDATE ON events
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE event_invite_tokens (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    token_hash bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) >= 32),
    created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    expires_at timestamptz,
    revoked_at timestamptz,
    last_used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_event_invite_active ON event_invite_tokens (event_id, expires_at)
WHERE revoked_at IS NULL;

CREATE TABLE saved_events (
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (user_id, event_id)
);

CREATE INDEX ix_saved_events_user_created ON saved_events (user_id, created_at DESC, event_id);

CREATE TABLE registrations (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    method registration_method NOT NULL,
    state registration_state NOT NULL,
    seat_held boolean NOT NULL DEFAULT false,
    waitlist_sequence bigint,
    cash_expires_at timestamptz,
    confirmed_at timestamptz,
    cancelled_at timestamptz,
    expired_at timestamptz,
    cancellation_reason text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_registrations_seat_state CHECK (
        (state = 'confirmed' AND seat_held AND confirmed_at IS NOT NULL AND waitlist_sequence IS NULL)
        OR (state = 'cash_pending' AND seat_held AND method = 'cash_organizer_confirmed'
            AND cash_expires_at IS NOT NULL AND waitlist_sequence IS NULL)
        OR (state = 'waitlisted' AND NOT seat_held AND waitlist_sequence IS NOT NULL)
        OR (state = 'cancelled' AND NOT seat_held AND cancelled_at IS NOT NULL)
        OR (state = 'expired' AND NOT seat_held AND method = 'cash_organizer_confirmed' AND expired_at IS NOT NULL)
    ),
    CONSTRAINT ck_registrations_free_method CHECK (method <> 'free' OR cash_expires_at IS NULL)
);

CREATE UNIQUE INDEX uq_registrations_active_member_event ON registrations (event_id, user_id)
WHERE state IN ('confirmed', 'cash_pending', 'waitlisted');
CREATE UNIQUE INDEX uq_registrations_waitlist_sequence ON registrations (event_id, waitlist_sequence)
WHERE state = 'waitlisted';
CREATE INDEX ix_registrations_capacity_lock ON registrations (event_id, state)
WHERE state IN ('confirmed', 'cash_pending');
CREATE INDEX ix_registrations_cash_expiry ON registrations (cash_expires_at, id)
WHERE state = 'cash_pending';
CREATE INDEX ix_registrations_member ON registrations (user_id, created_at DESC);
CREATE INDEX ix_registrations_attendee_list ON registrations (event_id, state, created_at, id);
CREATE TRIGGER registrations_set_updated_at
BEFORE UPDATE ON registrations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE registration_transitions (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    registration_id uuid NOT NULL REFERENCES registrations(id) ON DELETE RESTRICT,
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    actor_kind text NOT NULL CHECK (actor_kind IN ('member', 'organizer', 'admin', 'system')),
    previous_state registration_state,
    new_state registration_state NOT NULL,
    reason_code text NOT NULL CHECK (reason_code ~ '^[a-z0-9_]+$'),
    safe_metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(safe_metadata) = 'object'),
    request_id uuid,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_registration_transition_changed CHECK (previous_state IS NULL OR previous_state <> new_state)
);

CREATE INDEX ix_registration_transitions_history ON registration_transitions (registration_id, created_at, id);
CREATE TRIGGER registration_transitions_immutable
BEFORE UPDATE OR DELETE ON registration_transitions
FOR EACH ROW EXECUTE FUNCTION reject_mutation();

CREATE TABLE idempotency_keys (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    http_method text NOT NULL CHECK (http_method IN ('POST', 'PUT', 'PATCH', 'DELETE')),
    route_fingerprint text NOT NULL,
    key text NOT NULL CHECK (length(key) BETWEEN 16 AND 200),
    request_hash bytea NOT NULL CHECK (octet_length(request_hash) = 32),
    response_status integer CHECK (response_status BETWEEN 100 AND 599),
    response_body jsonb,
    locked_until timestamptz,
    completed_at timestamptz,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_idempotency_scope UNIQUE (user_id, http_method, route_fingerprint, key),
    CONSTRAINT ck_idempotency_response_shape CHECK (
        (completed_at IS NULL AND response_status IS NULL AND response_body IS NULL)
        OR (completed_at IS NOT NULL AND response_status IS NOT NULL AND response_body IS NOT NULL)
    )
);

CREATE INDEX ix_idempotency_cleanup ON idempotency_keys (expires_at);

CREATE TABLE announcements (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    club_id uuid NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    author_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 160),
    body text NOT NULL CHECK (length(btrim(body)) BETWEEN 1 AND 10000),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_announcements_club ON announcements (club_id, published_at DESC, id);
CREATE TRIGGER announcements_set_updated_at
BEFORE UPDATE ON announcements
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE event_updates (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    author_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 160),
    body text NOT NULL CHECK (length(btrim(body)) BETWEEN 1 AND 10000),
    change_summary jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(change_summary) = 'object'),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_event_updates_event ON event_updates (event_id, published_at DESC, id);

CREATE TABLE notifications (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    recipient_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type_key text NOT NULL CHECK (type_key ~ '^[a-z0-9_.]+$'),
    title_key text NOT NULL,
    body_key text NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(parameters) = 'object'),
    action_path text CHECK (action_path IS NULL OR action_path ~ '^/'),
    source_type text,
    source_id uuid,
    read_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_notifications_inbox ON notifications (recipient_user_id, created_at DESC, id);
CREATE INDEX ix_notifications_unread ON notifications (recipient_user_id, created_at DESC)
WHERE read_at IS NULL;

CREATE TABLE notification_deliveries (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    notification_id uuid NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel notification_channel NOT NULL,
    status delivery_status NOT NULL DEFAULT 'pending',
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at timestamptz,
    provider_message_id text,
    last_error_code text,
    processing_started_at timestamptz,
    delivered_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_notification_delivery_channel UNIQUE (notification_id, channel),
    CONSTRAINT ck_notification_delivery_delivered CHECK (status <> 'delivered' OR delivered_at IS NOT NULL)
);

CREATE INDEX ix_notification_delivery_queue ON notification_deliveries (status, next_attempt_at, id)
WHERE status IN ('pending', 'retryable_failed');
CREATE TRIGGER notification_deliveries_set_updated_at
BEFORE UPDATE ON notification_deliveries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE outbox_events (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    aggregate_type text NOT NULL CHECK (aggregate_type ~ '^[a-z0-9_]+$'),
    aggregate_id uuid NOT NULL,
    event_type text NOT NULL CHECK (event_type ~ '^[a-z0-9_.]+$'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    deduplication_key text NOT NULL UNIQUE,
    status delivery_status NOT NULL DEFAULT 'pending',
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    locked_until timestamptz,
    locked_by text,
    last_error_code text,
    processed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_outbox_lock_shape CHECK ((locked_until IS NULL) = (locked_by IS NULL)),
    CONSTRAINT ck_outbox_processed_shape CHECK (status <> 'delivered' OR processed_at IS NOT NULL)
);

CREATE INDEX ix_outbox_claim ON outbox_events (available_at, id)
WHERE status IN ('pending', 'retryable_failed');
CREATE INDEX ix_outbox_stale_locks ON outbox_events (locked_until)
WHERE locked_until IS NOT NULL AND processed_at IS NULL;

CREATE TABLE moderation_cases (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    reporter_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    target_type moderation_target_type NOT NULL,
    target_user_id uuid REFERENCES users(id) ON DELETE RESTRICT,
    target_club_id uuid REFERENCES clubs(id) ON DELETE RESTRICT,
    target_event_id uuid REFERENCES events(id) ON DELETE RESTRICT,
    category text NOT NULL CHECK (category IN ('safety', 'harassment', 'fraud', 'illegal_content', 'privacy', 'spam', 'other')),
    description text NOT NULL CHECK (length(btrim(description)) BETWEEN 10 AND 5000),
    status moderation_case_status NOT NULL DEFAULT 'open',
    priority moderation_priority NOT NULL DEFAULT 'standard',
    assigned_admin_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    resolution_reason text,
    acknowledged_at timestamptz,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_moderation_target_shape CHECK (
        (target_type = 'user' AND target_user_id IS NOT NULL AND target_club_id IS NULL AND target_event_id IS NULL)
        OR (target_type = 'club' AND target_user_id IS NULL AND target_club_id IS NOT NULL AND target_event_id IS NULL)
        OR (target_type = 'event' AND target_user_id IS NULL AND target_club_id IS NULL AND target_event_id IS NOT NULL)
    ),
    CONSTRAINT ck_moderation_resolution_shape CHECK (
        status NOT IN ('actioned', 'dismissed') OR (resolution_reason IS NOT NULL AND resolved_at IS NOT NULL)
    )
);

CREATE INDEX ix_moderation_queue ON moderation_cases (status, priority, created_at, id)
WHERE status IN ('open', 'investigating');
CREATE INDEX ix_moderation_assignee ON moderation_cases (assigned_admin_user_id, status, created_at)
WHERE assigned_admin_user_id IS NOT NULL;
CREATE TRIGGER moderation_cases_set_updated_at
BEFORE UPDATE ON moderation_cases
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE moderation_case_events (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    moderation_case_id uuid NOT NULL REFERENCES moderation_cases(id) ON DELETE RESTRICT,
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    action moderation_action,
    from_status moderation_case_status,
    to_status moderation_case_status NOT NULL,
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 2000),
    safe_metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(safe_metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_moderation_case_events_history ON moderation_case_events (moderation_case_id, created_at, id);
CREATE TRIGGER moderation_case_events_immutable
BEFORE UPDATE OR DELETE ON moderation_case_events
FOR EACH ROW EXECUTE FUNCTION reject_mutation();

CREATE TABLE audit_events (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    actor_kind text NOT NULL CHECK (actor_kind IN ('member', 'organizer', 'admin', 'system')),
    action text NOT NULL CHECK (action ~ '^[a-z0-9_.]+$'),
    target_type text NOT NULL CHECK (target_type ~ '^[a-z0-9_]+$'),
    target_id uuid,
    reason text,
    safe_before jsonb CHECK (safe_before IS NULL OR jsonb_typeof(safe_before) = 'object'),
    safe_after jsonb CHECK (safe_after IS NULL OR jsonb_typeof(safe_after) = 'object'),
    request_id uuid,
    ip_prefix inet,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX ix_audit_target ON audit_events (target_type, target_id, created_at DESC, id);
CREATE INDEX ix_audit_actor ON audit_events (actor_user_id, created_at DESC, id);
CREATE INDEX ix_audit_request ON audit_events (request_id) WHERE request_id IS NOT NULL;
CREATE TRIGGER audit_events_immutable
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION reject_mutation();

CREATE TABLE platform_settings (
    key text PRIMARY KEY CHECK (key ~ '^[a-z0-9_.]+$'),
    value jsonb NOT NULL,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    updated_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TRIGGER platform_settings_set_updated_at
BEFORE UPDATE ON platform_settings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO countries (id, code, name_key, default_locale, default_currency)
VALUES
    ('01900000-0000-7000-8000-000000000001', 'TR', 'countries.tr', 'tr', 'TRY'),
    ('01900000-0000-7000-8000-000000000002', 'DZ', 'countries.dz', 'ar', 'DZD');

INSERT INTO cities (id, country_id, slug, name_key, time_zone, latitude, longitude, beta_enabled)
VALUES
    ('01900000-0000-7000-8000-000000000101', '01900000-0000-7000-8000-000000000001', 'istanbul', 'cities.istanbul', 'Europe/Istanbul', 41.008238, 28.978359, true),
    ('01900000-0000-7000-8000-000000000102', '01900000-0000-7000-8000-000000000002', 'algiers', 'cities.algiers', 'Africa/Algiers', 36.753768, 3.058756, true);

INSERT INTO categories (id, slug, name_key, icon_key, sort_order)
VALUES
    ('01900000-0000-7000-8000-000000000201', 'sports', 'categories.sports', 'ball', 10),
    ('01900000-0000-7000-8000-000000000202', 'outdoors', 'categories.outdoors', 'mountain', 20),
    ('01900000-0000-7000-8000-000000000203', 'education', 'categories.education', 'book', 30),
    ('01900000-0000-7000-8000-000000000204', 'culture', 'categories.culture', 'landmark', 40),
    ('01900000-0000-7000-8000-000000000205', 'social', 'categories.social', 'users', 50),
    ('01900000-0000-7000-8000-000000000206', 'wellness', 'categories.wellness', 'heart', 60);

INSERT INTO regional_policies (
    country_id,
    allowed_registration_methods,
    cash_expiry_default_minutes,
    cash_expiry_min_minutes,
    cash_expiry_max_minutes,
    cancellation_default_minutes,
    cancellation_min_minutes,
    cancellation_max_minutes,
    default_club_ownership_limit,
    default_active_independent_event_limit,
    exact_venue_public_by_default
)
VALUES
    (
        '01900000-0000-7000-8000-000000000001',
        ARRAY['free', 'cash_organizer_confirmed']::registration_method[],
        1440, 120, 4320,
        1440, 0, 10080,
        1, 3, false
    ),
    (
        '01900000-0000-7000-8000-000000000002',
        ARRAY['free', 'cash_organizer_confirmed']::registration_method[],
        2880, 120, 10080,
        1440, 0, 10080,
        1, 3, false
    );

INSERT INTO platform_settings (key, value)
VALUES
    ('billing.enabled', 'false'::jsonb),
    ('beta.minimum_age', '18'::jsonb),
    ('features.google_oauth', 'false'::jsonb),
    ('features.redis_required', 'false'::jsonb),
    ('policies.terms_version', '"2026-07-11"'::jsonb),
    ('policies.privacy_version', '"2026-07-11"'::jsonb),
    ('policies.organizer_rules_version', '"2026-07-11"'::jsonb),
    ('policies.community_rules_version', '"2026-07-11"'::jsonb);

COMMENT ON SCHEMA talaqi IS 'Talaqi closed-beta transactional schema';
COMMENT ON COLUMN users.password_hash IS 'Argon2id encoded hash; never plaintext or reversible encryption';
COMMENT ON COLUMN sessions.refresh_token_hash IS 'SHA-256 or stronger digest of a high-entropy refresh token';
COMMENT ON COLUMN auth_tokens.token_hash IS 'Digest only; raw verification/reset tokens are never stored';
COMMENT ON COLUMN event_invite_tokens.token_hash IS 'Digest only; raw private-link tokens are never stored or logged';
COMMENT ON COLUMN events.exact_address IS 'Return only to managers and confirmed or unexpired cash-pending attendees unless exact_venue_is_public';
COMMENT ON TABLE registration_transitions IS 'Append-only registration state history';
COMMENT ON TABLE audit_events IS 'Append-only security and operational audit history';

COMMIT;
