BEGIN;
SET LOCAL search_path = talaqi, public;

DO $test$
DECLARE
    missing_tables text[];
    required_tables constant text[] := ARRAY[
        'schema_revisions', 'users', 'profiles', 'sessions', 'auth_tokens',
        'countries', 'cities', 'categories', 'regional_policies',
        'media_assets', 'clubs', 'club_memberships', 'club_join_requests',
        'events', 'event_invite_tokens', 'saved_events', 'registrations',
        'registration_transitions', 'announcements', 'event_updates',
        'notifications', 'notification_deliveries', 'outbox_events',
        'moderation_cases', 'moderation_case_events', 'audit_events',
        'idempotency_keys', 'platform_settings', 'user_mfa_factors'
    ];
BEGIN
    SELECT array_agg(name ORDER BY name)
      INTO missing_tables
      FROM unnest(required_tables) AS name
     WHERE to_regclass('talaqi.' || name) IS NULL;

    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required tables: %', missing_tables;
    END IF;
END
$test$;

DO $test$
DECLARE
    required_types constant text[] := ARRAY[
        'user_status', 'club_membership_policy', 'club_role', 'club_status',
        'event_ownership_type', 'event_visibility', 'event_status',
        'registration_method', 'registration_state', 'notification_channel',
        'delivery_status', 'moderation_target_type', 'moderation_case_status',
        'moderation_priority', 'moderation_action'
    ];
    missing_types text[];
BEGIN
    SELECT array_agg(name ORDER BY name)
      INTO missing_types
      FROM unnest(required_types) AS name
     WHERE NOT EXISTS (
         SELECT 1
           FROM pg_type t
           JOIN pg_namespace n ON n.oid = t.typnamespace
          WHERE n.nspname = 'talaqi' AND t.typname = name
     );

    IF missing_types IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required enum types: %', missing_types;
    END IF;
END
$test$;

DO $test$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'talaqi'
           AND indexname = 'uq_registrations_active_member_event'
           AND indexdef ILIKE '%WHERE%'
    ) THEN
        RAISE EXCEPTION 'Missing partial unique active-registration index';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'talaqi'
           AND indexname = 'uq_club_memberships_single_owner'
           AND indexdef ILIKE '%WHERE%'
    ) THEN
        RAISE EXCEPTION 'Missing partial unique club-owner index';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
         WHERE tgname = 'audit_events_immutable'
           AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'Missing immutable audit-event trigger';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
         WHERE tgname = 'registration_transitions_immutable'
           AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'Missing immutable registration-transition trigger';
    END IF;
END
$test$;

DO $test$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.table_constraints
         WHERE constraint_schema = 'talaqi'
           AND table_name = 'events'
           AND constraint_name = 'ck_events_owner_shape'
    ) THEN
        RAISE EXCEPTION 'Missing event ownership-shape constraint';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.table_constraints
         WHERE constraint_schema = 'talaqi'
           AND table_name = 'events'
           AND constraint_name = 'ck_events_coordinates_pair'
    ) THEN
        RAISE EXCEPTION 'Missing paired-coordinate constraint';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.table_constraints
         WHERE constraint_schema = 'talaqi'
           AND table_name = 'registrations'
           AND constraint_name = 'ck_registrations_seat_state'
    ) THEN
        RAISE EXCEPTION 'Missing registration seat/state constraint';
    END IF;
END
$test$;

ROLLBACK;

SELECT true AS passed, 'Talaqi schema contract passed.' AS message;
