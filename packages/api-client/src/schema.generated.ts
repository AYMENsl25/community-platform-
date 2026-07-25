export interface paths {
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login Account */
        post: operations["loginAccount"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout Account */
        post: operations["logoutAccount"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password-reset/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Password Reset */
        post: operations["confirmPasswordReset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password-reset/request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Password Reset */
        post: operations["requestPasswordReset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Session */
        post: operations["refreshSession"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register Account */
        post: operations["registerAccount"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sessions */
        get: operations["listSessions"];
        put?: never;
        post?: never;
        /** Revoke All Sessions */
        delete: operations["revokeAllSessions"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Session */
        delete: operations["revokeSession"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/verification/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Verification */
        post: operations["confirmEmailVerification"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/verification/request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Verification */
        post: operations["requestEmailVerification"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Categories */
        get: operations["listCategories"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/cities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cities */
        get: operations["listCities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Clubs */
        get: operations["listClubs"];
        put?: never;
        /** Create Club */
        post: operations["createClub"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Managed Club */
        get: operations["getManagedClub"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Club */
        patch: operations["updateClub"];
        trace?: never;
    };
    "/api/v1/clubs/{slug}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Club */
        get: operations["getClub"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/countries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Countries */
        get: operations["listCountries"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Events */
        get: operations["listEvents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Event */
        get: operations["getEvent"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/saved": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Save Event */
        put: operations["saveEvent"];
        post?: never;
        /** Unsave Event */
        delete: operations["unsaveEvent"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get My Profile */
        get: operations["getMyProfile"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Replace My Profile */
        patch: operations["replaceMyProfile"];
        trace?: never;
    };
    "/api/v1/me/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get My Capabilities */
        get: operations["getMyCapabilities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/saved-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Saved Events */
        get: operations["listSavedEvents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Metadata */
        get: operations["getDiscoveryMetadata"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/regions/{country_code}/policy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Region Policy */
        get: operations["getRegionPolicy"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Discovery */
        get: operations["searchDiscovery"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Live */
        get: operations["healthLive"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["healthReady"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AcceptedResponse */
        AcceptedResponse: {
            /**
             * Accepted
             * @default true
             * @constant
             */
            accepted: true;
        };
        /** AuthenticationResponse */
        AuthenticationResponse: {
            /**
             * Authenticated
             * @default true
             * @constant
             */
            authenticated: true;
            /** Email Verified */
            email_verified: boolean;
            /**
             * Status
             * @default active
             * @constant
             */
            status: "active";
        };
        /** Capabilities */
        Capabilities: {
            /** Access Admin */
            access_admin: boolean;
            /** Blockers */
            blockers: string[];
            /** Create Club */
            create_club: boolean;
            /** Create Independent Event */
            create_independent_event: boolean;
            /** Register Event */
            register_event: boolean;
            /** Save Event */
            save_event: boolean;
        };
        /** CategoryResponse */
        CategoryResponse: {
            /** Icon Key */
            icon_key: string;
            /** Name Key */
            name_key: string;
            /** Slug */
            slug: string;
            /** Sort Order */
            sort_order: number;
        };
        /** CityResponse */
        CityResponse: {
            /** Beta Enabled */
            beta_enabled: boolean;
            /** Country Code */
            country_code: string;
            /** Name Key */
            name_key: string;
            /** Slug */
            slug: string;
            /** Time Zone */
            time_zone: string;
        };
        /** ClubCardResponse */
        ClubCardResponse: {
            /** Category Slug */
            category_slug: string;
            /** City Slug */
            city_slug: string;
            /** Country Code */
            country_code: string;
            /** Cover Storage Key */
            cover_storage_key: string | null;
            /** Description */
            description: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Slug */
            slug: string;
        };
        /** ClubCreateRequest */
        ClubCreateRequest: {
            /** Category Slug */
            category_slug?: string | null;
            /** City Slug */
            city_slug?: string | null;
            /** Country Code */
            country_code?: string | null;
            /** Cover Media Id */
            cover_media_id?: string | null;
            /** Description */
            description?: string | null;
            /** Logo Media Id */
            logo_media_id?: string | null;
            /**
             * Membership Policy
             * @default open
             * @enum {string}
             */
            membership_policy: "open" | "approval_required";
            /** Name */
            name: string;
            /** Slug */
            slug: string;
            /** Social Links */
            social_links?: {
                [key: string]: string;
            };
        };
        /** ClubDetailResponse */
        ClubDetailResponse: {
            /** Category Slug */
            category_slug: string;
            /** City Slug */
            city_slug: string;
            /** Country Code */
            country_code: string;
            /** Cover Storage Key */
            cover_storage_key: string | null;
            /** Description */
            description: string;
            /** Events */
            events: components["schemas"]["EventCardResponse"][];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Slug */
            slug: string;
        };
        /** ClubPageResponse */
        ClubPageResponse: {
            /** Items */
            items: components["schemas"]["ClubCardResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ClubPatchRequest */
        ClubPatchRequest: {
            /** Category Slug */
            category_slug?: string | null;
            /** City Slug */
            city_slug?: string | null;
            /** Country Code */
            country_code?: string | null;
            /** Cover Media Id */
            cover_media_id?: string | null;
            /** Description */
            description?: string | null;
            /** Logo Media Id */
            logo_media_id?: string | null;
            /** Membership Policy */
            membership_policy?: ("open" | "approval_required") | null;
            /** Name */
            name?: string | null;
            /** Revision */
            revision: number;
            /** Slug */
            slug?: string | null;
            /** Social Links */
            social_links?: {
                [key: string]: string;
            } | null;
        };
        /** ClubResponse */
        ClubResponse: {
            /** Category Slug */
            category_slug: string | null;
            /** City Slug */
            city_slug: string | null;
            /** Closed At */
            closed_at: string | null;
            /** Country Code */
            country_code: string | null;
            /** Cover Media Id */
            cover_media_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Description */
            description: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Logo Media Id */
            logo_media_id: string | null;
            /**
             * Membership Policy
             * @enum {string}
             */
            membership_policy: "open" | "approval_required";
            /** Missing Fields */
            missing_fields: string[];
            /** Name */
            name: string;
            /** Published At */
            published_at: string | null;
            /** Revision */
            revision: number;
            /** Slug */
            slug: string;
            /** Social Links */
            social_links: {
                [key: string]: string;
            };
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "published" | "unpublished" | "suspended" | "closed";
            /** Suspended At */
            suspended_at: string | null;
            /** Suspension Reason */
            suspension_reason: string | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ConfirmedResponse */
        ConfirmedResponse: {
            /**
             * Confirmed
             * @default true
             * @constant
             */
            confirmed: true;
        };
        /** CountryResponse */
        CountryResponse: {
            /** Code */
            code: string;
            /** Default Currency */
            default_currency: string;
            /**
             * Default Locale
             * @enum {string}
             */
            default_locale: "en" | "tr" | "fr" | "ar";
            /** Name Key */
            name_key: string;
        };
        /** CursorPage */
        CursorPage: {
            items: unknown[];
            next_cursor: string | null;
        };
        /** DiscoveryMetadataResponse */
        DiscoveryMetadataResponse: {
            /** Categories */
            categories: {
                [key: string]: string;
            }[];
            /** Cities */
            cities: {
                [key: string]: string;
            }[];
            /** Countries */
            countries: {
                [key: string]: string;
            }[];
            /**
             * Price Types
             * @default [
             *       "free",
             *       "cash"
             *     ]
             */
            price_types: [
                "free",
                "cash"
            ];
            /**
             * Sort
             * @default featured
             * @constant
             */
            sort: "featured";
        };
        /** ErrorDetail */
        ErrorDetail: {
            code: string;
            field_errors: components["schemas"]["FieldError"][];
            message_key: string;
            /** Format: uuid */
            request_id: string;
        };
        /** ErrorEnvelope */
        ErrorEnvelope: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** EventCardResponse */
        EventCardResponse: {
            /** Available Places */
            available_places: number;
            /** Capacity */
            capacity: number;
            /** Category Slug */
            category_slug: string;
            /** City Slug */
            city_slug: string;
            /** Club Name */
            club_name: string | null;
            /** Club Slug */
            club_slug: string | null;
            /** Country Code */
            country_code: string;
            /** Cover Storage Key */
            cover_storage_key: string | null;
            /** Description */
            description: string;
            /** District */
            district: string | null;
            /**
             * End At
             * Format: date-time
             */
            end_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Is Saved */
            is_saved: boolean;
            /** Organizer Display Name */
            organizer_display_name: string | null;
            /**
             * Price Type
             * @enum {string}
             */
            price_type: "free" | "cash";
            /** Public Meeting Area */
            public_meeting_area: string | null;
            /** Registration State */
            registration_state: string | null;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /** Time Zone */
            time_zone: string;
            /** Title */
            title: string;
        };
        /** EventPageResponse */
        EventPageResponse: {
            /** Items */
            items: components["schemas"]["EventCardResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** FieldError */
        FieldError: {
            code: string;
            field: string;
            message_key: string;
        };
        /** LiveResponse */
        LiveResponse: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** LoginRequest */
        LoginRequest: {
            /** Identifier */
            identifier: string;
            /** Password */
            password: string;
        };
        /** LogoutResponse */
        LogoutResponse: {
            /**
             * Logged Out
             * @default true
             * @constant
             */
            logged_out: true;
        };
        /** PasswordResetConfirm */
        PasswordResetConfirm: {
            /** New Password */
            new_password: string;
            /** Token */
            token: string;
        };
        /** ProfileReplacementRequest */
        ProfileReplacementRequest: {
            /** City Slug */
            city_slug: string;
            /** Community Rules Version */
            community_rules_version: string;
            /** Country Code */
            country_code: string;
            /** Display Name */
            display_name: string;
            /**
             * Locale
             * @enum {string}
             */
            locale: "en" | "tr" | "fr" | "ar";
            /** Notify Community Email */
            notify_community_email: boolean;
            /** Notify Event Email */
            notify_event_email: boolean;
            /** Organizer Rules Version */
            organizer_rules_version: string;
            /** Preferred Currency */
            preferred_currency: string;
            /** Time Zone */
            time_zone: string;
            /** Username */
            username: string;
        };
        /** ProfileResponse */
        ProfileResponse: {
            /** Avatar */
            avatar?: null;
            /** City Slug */
            city_slug: string | null;
            /** Community Rules Version */
            community_rules_version: string | null;
            /** Country Code */
            country_code: string | null;
            /** Display Name */
            display_name: string | null;
            /** Locale */
            locale: ("en" | "tr" | "fr" | "ar") | null;
            /** Notify Community Email */
            notify_community_email: boolean;
            /** Notify Event Email */
            notify_event_email: boolean;
            /**
             * Notify Security Email
             * @constant
             */
            notify_security_email: true;
            /** Organizer Rules Version */
            organizer_rules_version: string | null;
            /** Preferred Currency */
            preferred_currency: string | null;
            /** Profile Completed At */
            profile_completed_at: string | null;
            /** Time Zone */
            time_zone: string | null;
            /** Username */
            username: string | null;
        };
        /** ReadyResponse */
        ReadyResponse: {
            /** Checks */
            checks: {
                [key: string]: "ok" | "failed";
            };
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "not_ready";
        };
        /** RecoveryConfirm */
        RecoveryConfirm: {
            /** Token */
            token: string;
        };
        /** RecoveryRequest */
        RecoveryRequest: {
            /** Email */
            email: string;
        };
        /** RefreshedResponse */
        RefreshedResponse: {
            /** Email Verified */
            email_verified: boolean;
            /**
             * Refreshed
             * @default true
             * @constant
             */
            refreshed: true;
        };
        /** RegionPolicyResponse */
        RegionPolicyResponse: {
            /** Allowed Registration Methods */
            allowed_registration_methods: string[];
            /** Cancellation Bounds */
            cancellation_bounds: [
                number,
                number
            ];
            /** Cancellation Default Minutes */
            cancellation_default_minutes: number;
            /** Cash Bounds */
            cash_bounds: [
                number,
                number
            ];
            /** Cash Default Minutes */
            cash_default_minutes: number;
            /** Club Limit */
            club_limit: number;
            /** Country Code */
            country_code: string;
            /** Default Currency */
            default_currency: string;
            /**
             * Default Locale
             * @enum {string}
             */
            default_locale: "en" | "tr" | "fr" | "ar";
            /** Exact Venue Public By Default */
            exact_venue_public_by_default: boolean;
            /** Independent Event Limit */
            independent_event_limit: number;
            /** Revision */
            revision: number;
        };
        /** RegistrationRequest */
        RegistrationRequest: {
            /**
             * Age Attested
             * @constant
             */
            age_attested: true;
            /** Email */
            email: string;
            /** Password */
            password: string;
            /** Privacy Version */
            privacy_version: string;
            /** Terms Version */
            terms_version: string;
        };
        /** RegistrationResponse */
        RegistrationResponse: {
            /**
             * Accepted
             * @default true
             * @constant
             */
            accepted: true;
        };
        /** RevokedResponse */
        RevokedResponse: {
            /**
             * Revoked
             * @default true
             * @constant
             */
            revoked: true;
        };
        /** SearchItemResponse */
        SearchItemResponse: {
            /** Category Slug */
            category_slug: string;
            /** City Slug */
            city_slug: string;
            /** Country Code */
            country_code: string;
            /** Description */
            description: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "event" | "club";
            /** Slug */
            slug: string | null;
            /** Start At */
            start_at: string | null;
            /** Title */
            title: string;
        };
        /** SearchPageResponse */
        SearchPageResponse: {
            /** Items */
            items: components["schemas"]["SearchItemResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** SessionResponse */
        SessionResponse: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Current */
            current: boolean;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Used At */
            last_used_at: string | null;
        };
        /** SessionsResponse */
        SessionsResponse: {
            /** Sessions */
            sessions: components["schemas"]["SessionResponse"][];
        };
    };
    responses: {
        /** @description A stable Talaqi platform error envelope. */
        PlatformError: {
            headers: {
                "X-Request-ID": components["headers"]["RequestId"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorEnvelope"];
            };
        };
    };
    parameters: never;
    requestBodies: never;
    headers: {
        /** @description Required on retryable mutation operations. */
        IdempotencyKey: string;
        /** @description A server-owned UUIDv7 request identifier. */
        RequestId: string;
    };
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    loginAccount: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthenticationResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    logoutAccount: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LogoutResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    confirmPasswordReset: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetConfirm"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConfirmedResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    requestPasswordReset: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecoveryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcceptedResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    refreshSession: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RefreshedResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    registerAccount: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegistrationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegistrationResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    listSessions: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionsResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    revokeAllSessions: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevokedResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    revokeSession: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevokedResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Authentication failed. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    confirmEmailVerification: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecoveryConfirm"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConfirmedResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    requestEmailVerification: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecoveryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcceptedResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
            /** @description The authentication request rate was exceeded. */
            429: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    listCategories: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryResponse"][];
                };
            };
        };
    };
    listCities: {
        parameters: {
            query?: {
                country_code?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CityResponse"][];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    listClubs: {
        parameters: {
            query?: {
                category?: string | null;
                city?: string | null;
                country?: string | null;
                cursor?: string | null;
                limit?: number;
                search?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClubPageResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    createClub: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying this club creation request. */
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClubCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClubResponse"];
                };
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Capability, object authorization, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Slug, revision, or idempotency conflict. */
            409: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getManagedClub: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                club_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClubResponse"];
                };
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Capability, object authorization, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Club not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    updateClub: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                club_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClubPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClubResponse"];
                };
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Capability, object authorization, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Club not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Slug, revision, or idempotency conflict. */
            409: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getClub: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slug: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClubDetailResponse"];
                };
            };
            /** @description Public resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    listCountries: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CountryResponse"][];
                };
            };
        };
    };
    listEvents: {
        parameters: {
            query?: {
                category?: string | null;
                city?: string | null;
                country?: string | null;
                cursor?: string | null;
                date_from?: string | null;
                date_to?: string | null;
                limit?: number;
                price?: string | null;
                search?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventPageResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventCardResponse"];
                };
            };
            /** @description Public resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    saveEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Capability or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Public resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    unsaveEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Capability or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Public resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getMyProfile: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    replaceMyProfile: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileReplacementRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileResponse"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description CSRF validation failed. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Username is unavailable. */
            409: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getMyCapabilities: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Capabilities"];
                };
            };
            /** @description Authentication failed. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    listSavedEvents: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventPageResponse"];
                };
            };
            /** @description Authentication required. */
            401: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    getDiscoveryMetadata: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscoveryMetadataResponse"];
                };
            };
        };
    };
    getRegionPolicy: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                country_code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegionPolicyResponse"];
                };
            };
            /** @description The requested enabled region does not exist. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    searchDiscovery: {
        parameters: {
            query: {
                category?: string | null;
                city?: string | null;
                country?: string | null;
                cursor?: string | null;
                limit?: number;
                search: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchPageResponse"];
                };
            };
            422: components["responses"]["PlatformError"];
        };
    };
    healthLive: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LiveResponse"];
                };
            };
        };
    };
    healthReady: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
            /** @description One or more readiness dependencies are unavailable. */
            503: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
        };
    };
}
