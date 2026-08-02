export interface paths {
    "/api/v1/admin/audit-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Audit Events */
        get: operations["listAdminAuditEvents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/moderation/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cases */
        get: operations["listModerationCases"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/moderation/cases/{case_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Case */
        get: operations["getModerationCase"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/moderation/cases/{case_id}/actions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Perform Action */
        post: operations["performModerationAction"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/moderation/targets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Targets */
        get: operations["searchModerationTargets"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
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
    "/api/v1/clubs/{club_id}/close": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Close Club */
        post: operations["closeClub"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/join": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Join Club */
        post: operations["joinClub"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/join-requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Club Join Requests */
        get: operations["listClubJoinRequests"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/join-requests/{join_request_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Club Join Request */
        post: operations["approveClubJoinRequest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/join-requests/{join_request_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Club Join Request */
        post: operations["rejectClubJoinRequest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Club Members */
        get: operations["listClubMembers"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/members/{user_id}/role": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Change Club Member Role */
        patch: operations["changeClubMemberRole"];
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/membership": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Leave Club */
        delete: operations["leaveClub"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/clubs/{club_id}/ownership-transfer": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Transfer Club Ownership */
        post: operations["transferClubOwnership"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/v1/clubs/managed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Managed Clubs */
        get: operations["listManagedClubs"];
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
    "/api/v1/event-access/resolve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Private Link */
        post: operations["resolveEventPrivateLink"];
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
        /** Create Event */
        post: operations["createEvent"];
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
        /** Delete Draft Event */
        delete: operations["deleteDraftEvent"];
        options?: never;
        head?: never;
        /** Update Event */
        patch: operations["updateEvent"];
        trace?: never;
    };
    "/api/v1/events/{event_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Event */
        post: operations["cancelEvent"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Event */
        post: operations["completeEvent"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/duplicate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Duplicate Event */
        post: operations["duplicateEvent"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/managed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Managed Event */
        get: operations["getManagedEvent"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/private-link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Private Link */
        post: operations["createEventPrivateLink"];
        /** Revoke Private Link */
        delete: operations["revokeEventPrivateLink"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/private-link/rotate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rotate Private Link */
        post: operations["rotateEventPrivateLink"];
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
    "/api/v1/events/managed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Managed Events */
        get: operations["listManagedEvents"];
        put?: never;
        post?: never;
        delete?: never;
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
    "/api/v1/media/public/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Public Media */
        get: operations["getPublicMedia"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Media Upload */
        post: operations["createMediaUpload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads/{asset_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Media Upload */
        post: operations["completeMediaUpload"];
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
        /** ActionRequest */
        ActionRequest: {
            /**
             * Action
             * @enum {string}
             */
            action: "suspend" | "unpublish" | "restore";
            /** Reason */
            reason: string;
        };
        /** ActionResponse */
        ActionResponse: {
            /**
             * Action
             * @enum {string}
             */
            action: "suspend" | "unpublish" | "restore";
            case: components["schemas"]["CaseResponse"];
            /** Events */
            events: components["schemas"]["CaseEventResponse"][];
            /**
             * Status
             * @default actioned
             * @constant
             */
            status: "actioned";
        };
        /** AuditPageResponse */
        AuditPageResponse: {
            /** Items */
            items: components["schemas"]["AuditResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** AuditResponse */
        AuditResponse: {
            /** Action */
            action: string;
            /** Actor Kind */
            actor_kind: string;
            /** Actor User Id */
            actor_user_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Reason */
            reason: string | null;
            /** Request Id */
            request_id: string | null;
            /** Safe After */
            safe_after: {
                [key: string]: unknown;
            } | null;
            /** Safe Before */
            safe_before: {
                [key: string]: unknown;
            } | null;
            /** Target Id */
            target_id: string | null;
            /** Target Type */
            target_type: string;
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
        /** CaseDetailResponse */
        CaseDetailResponse: {
            case: components["schemas"]["CaseResponse"];
            /** Events */
            events: components["schemas"]["CaseEventResponse"][];
        };
        /** CaseEventResponse */
        CaseEventResponse: {
            /** Action */
            action: string | null;
            /** Actor User Id */
            actor_user_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** From Status */
            from_status: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Reason */
            reason: string;
            /** To Status */
            to_status: string;
        };
        /** CasePageResponse */
        CasePageResponse: {
            /** Items */
            items: components["schemas"]["CaseResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CaseResponse */
        CaseResponse: {
            /** Acknowledged At */
            acknowledged_at: string | null;
            /** Assigned Admin User Id */
            assigned_admin_user_id: string | null;
            /** Available Actions */
            available_actions: ("suspend" | "unpublish" | "restore")[];
            /** Category */
            category: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Emergency Notice */
            emergency_notice: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Priority
             * @enum {string}
             */
            priority: "standard" | "high" | "emergency";
            /** Resolution Reason */
            resolution_reason: string | null;
            /** Resolved At */
            resolved_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "investigating" | "actioned" | "dismissed";
            target: components["schemas"]["TargetResponse"];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
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
        /** CloseClubRequest */
        CloseClubRequest: {
            /** Reason */
            reason: string;
        };
        /** ClubCardResponse */
        ClubCardResponse: {
            /** Category Slug */
            category_slug: string;
            /** City Slug */
            city_slug: string;
            /** Country Code */
            country_code: string;
            /** Cover Media Id */
            cover_media_id: string | null;
            /** Description */
            description: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Member Count */
            member_count: number;
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
            /** Cover Media Id */
            cover_media_id: string | null;
            /** Description */
            description: string;
            /** Events */
            events: components["schemas"]["EventCardResponse"][];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Member Count */
            member_count: number;
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
        /** DecisionRequest */
        DecisionRequest: {
            /** Reason */
            reason: string;
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
        /** EventAudienceResponse */
        EventAudienceResponse: {
            /** Available Places */
            available_places: number | null;
            /** Cancellation Cutoff Minutes */
            cancellation_cutoff_minutes: number;
            /** Capacity */
            capacity: number | null;
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
            /** Cover Media Id */
            cover_media_id: string | null;
            /** Description */
            description: string;
            /** District */
            district: string | null;
            /**
             * End At
             * Format: date-time
             */
            end_at: string;
            /** Exact Address */
            exact_address: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Is Saved */
            is_saved: boolean;
            /** Latitude */
            latitude: number | null;
            /** Longitude */
            longitude: number | null;
            /** Organizer Display Name */
            organizer_display_name: string | null;
            /**
             * Ownership Type
             * @enum {string}
             */
            ownership_type: "club" | "independent";
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
        /** EventCardResponse */
        EventCardResponse: {
            /** Available Places */
            available_places: number | null;
            /** Cancellation Cutoff Minutes */
            cancellation_cutoff_minutes: number;
            /** Capacity */
            capacity: number | null;
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
            /** Cover Media Id */
            cover_media_id: string | null;
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
             * Ownership Type
             * @enum {string}
             */
            ownership_type: "club" | "independent";
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
        /** EventCreateRequest */
        EventCreateRequest: {
            /** Cancellation Cutoff Minutes */
            cancellation_cutoff_minutes?: number | null;
            /** Capacity */
            capacity?: number | null;
            /** Cash Expiry Minutes */
            cash_expiry_minutes?: number | null;
            /** Category Slug */
            category_slug?: string | null;
            /** City Slug */
            city_slug?: string | null;
            /** Club Id */
            club_id?: string | null;
            /** Country Code */
            country_code?: string | null;
            /** Cover Media Id */
            cover_media_id?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** District */
            district?: string | null;
            /** End At */
            end_at?: string | null;
            /** Exact Address */
            exact_address?: string | null;
            /**
             * Exact Venue Is Public
             * @default false
             */
            exact_venue_is_public: boolean;
            /** Latitude */
            latitude?: number | null;
            /** Longitude */
            longitude?: number | null;
            /**
             * Ownership Type
             * @enum {string}
             */
            ownership_type: "club" | "independent";
            /** Public Meeting Area */
            public_meeting_area?: string | null;
            /**
             * Publish
             * @default false
             */
            publish: boolean;
            /** Registration Method */
            registration_method?: ("free" | "cash_organizer_confirmed") | null;
            /** Start At */
            start_at?: string | null;
            /** Time Zone */
            time_zone?: string | null;
            /** Title */
            title: string;
            /**
             * Visibility
             * @default public
             * @enum {string}
             */
            visibility: "public" | "private_link";
        };
        /** EventPageResponse */
        EventPageResponse: {
            /** Items */
            items: components["schemas"]["EventCardResponse"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** EventPatchRequest */
        EventPatchRequest: {
            /** Cancellation Cutoff Minutes */
            cancellation_cutoff_minutes?: number | null;
            /** Capacity */
            capacity?: number | null;
            /** Cash Expiry Minutes */
            cash_expiry_minutes?: number | null;
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
            /** District */
            district?: string | null;
            /** End At */
            end_at?: string | null;
            /** Exact Address */
            exact_address?: string | null;
            /** Exact Venue Is Public */
            exact_venue_is_public?: boolean | null;
            /** Latitude */
            latitude?: number | null;
            /** Longitude */
            longitude?: number | null;
            /** Public Meeting Area */
            public_meeting_area?: string | null;
            /** Publish */
            publish?: boolean | null;
            /** Registration Method */
            registration_method?: ("free" | "cash_organizer_confirmed") | null;
            /** Revision */
            revision: number;
            /** Start At */
            start_at?: string | null;
            /** Time Zone */
            time_zone?: string | null;
            /** Title */
            title?: string | null;
            /** Visibility */
            visibility?: ("public" | "private_link") | null;
        };
        /** EventRevisionRequest */
        EventRevisionRequest: {
            /** Revision */
            revision: number;
        };
        /** FieldError */
        FieldError: {
            code: string;
            field: string;
            message_key: string;
        };
        /** JoinClubRequest */
        JoinClubRequest: {
            /** Message */
            message?: string | null;
        };
        /** JoinClubResponse */
        JoinClubResponse: {
            /** Join Request Id */
            join_request_id: string | null;
            /** Membership Id */
            membership_id: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "member" | "pending";
        };
        /** JoinRequestPageResponse */
        JoinRequestPageResponse: {
            /** Items */
            items: components["schemas"]["JoinRequestResponse"][];
        };
        /** JoinRequestResponse */
        JoinRequestResponse: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Decided At */
            decided_at: string | null;
            /** Decision Reason */
            decision_reason: string | null;
            /** Display Name */
            display_name: string | null;
            /** Email */
            email: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Message */
            message: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "approved" | "rejected" | "cancelled";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
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
        /** ManagedClubPageResponse */
        ManagedClubPageResponse: {
            /** Items */
            items: components["schemas"]["ManagedClubResponse"][];
        };
        /** ManagedClubResponse */
        ManagedClubResponse: {
            /** Capabilities */
            capabilities: ("edit_profile" | "manage_members" | "change_member_roles" | "transfer_ownership" | "close_club" | "preview_profile")[];
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
            /**
             * Role
             * @enum {string}
             */
            role: "owner" | "admin";
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
        /** ManagedEventPageResponse */
        ManagedEventPageResponse: {
            /** Items */
            items: components["schemas"]["ManagedEventResponse"][];
        };
        /** ManagedEventResponse */
        ManagedEventResponse: {
            /** Cancellation Cutoff Minutes */
            cancellation_cutoff_minutes: number | null;
            /** Cancelled At */
            cancelled_at: string | null;
            /**
             * Capabilities
             * @default []
             */
            capabilities: ("edit" | "duplicate" | "cancel" | "complete" | "delete_draft" | "preview")[];
            /** Capacity */
            capacity: number | null;
            /** Cash Expiry Minutes */
            cash_expiry_minutes: number | null;
            /** Category Slug */
            category_slug: string | null;
            /** City Slug */
            city_slug: string | null;
            /** Club Id */
            club_id: string | null;
            /** Completed At */
            completed_at: string | null;
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
            description: string;
            /** District */
            district: string | null;
            /** End At */
            end_at: string | null;
            /** Exact Address */
            exact_address: string | null;
            /** Exact Venue Is Public */
            exact_venue_is_public: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Latitude */
            latitude: number | null;
            /** Longitude */
            longitude: number | null;
            /** Owner User Id */
            owner_user_id: string | null;
            /**
             * Ownership Type
             * @enum {string}
             */
            ownership_type: "club" | "independent";
            /** Public Meeting Area */
            public_meeting_area: string | null;
            /** Published At */
            published_at: string | null;
            /** Registration Method */
            registration_method: ("free" | "cash_organizer_confirmed") | null;
            /** Revision */
            revision: number;
            /** Start At */
            start_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "published" | "cancelled" | "completed" | "suspended";
            /** Suspended At */
            suspended_at: string | null;
            /** Suspension Reason */
            suspension_reason: string | null;
            /** Time Zone */
            time_zone: string | null;
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Validation Blockers
             * @default []
             */
            validation_blockers: string[];
            /**
             * Visibility
             * @enum {string}
             */
            visibility: "public" | "private_link";
        };
        /** MediaAssetResponse */
        MediaAssetResponse: {
            /** Byte Size */
            byte_size: number;
            /** Content Type */
            content_type: string;
            /** Height */
            height: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "verified";
            /** Verified At */
            verified_at: string | null;
            /** Width */
            width: number | null;
        };
        /** MediaUploadCreateRequest */
        MediaUploadCreateRequest: {
            /** Byte Size */
            byte_size: number;
            /**
             * Content Type
             * @enum {string}
             */
            content_type: "image/jpeg" | "image/png" | "image/webp";
            /** Original Filename */
            original_filename: string;
        };
        /** MediaUploadResponse */
        MediaUploadResponse: {
            /** Byte Size */
            byte_size: number;
            /** Content Type */
            content_type: string;
            /** Height */
            height: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "verified";
            upload: components["schemas"]["UploadGrantResponse"];
            /** Verified At */
            verified_at: string | null;
            /** Width */
            width: number | null;
        };
        /** MemberPageResponse */
        MemberPageResponse: {
            /** Items */
            items: components["schemas"]["MemberResponse"][];
        };
        /** MemberResponse */
        MemberResponse: {
            /** Display Name */
            display_name: string | null;
            /** Email */
            email: string | null;
            /**
             * Joined At
             * Format: date-time
             */
            joined_at: string;
            /**
             * Role
             * @enum {string}
             */
            role: "owner" | "admin" | "member";
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** OperationResponse */
        OperationResponse: {
            /**
             * Status
             * @enum {string}
             */
            status: "left" | "approved" | "rejected" | "role_changed" | "transferred" | "closed";
        };
        /** OwnershipTransferRequest */
        OwnershipTransferRequest: {
            /** Reason */
            reason: string;
            /**
             * Target User Id
             * Format: uuid
             */
            target_user_id: string;
        };
        /** PasswordResetConfirm */
        PasswordResetConfirm: {
            /** New Password */
            new_password: string;
            /** Token */
            token: string;
        };
        /** PrivateLinkCreateRequest */
        PrivateLinkCreateRequest: {
            /**
             * Expires In Days
             * @default 30
             */
            expires_in_days: number;
        };
        /** PrivateLinkIssuedResponse */
        PrivateLinkIssuedResponse: {
            /** Copy Value */
            copy_value: string;
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** PrivateLinkResolveRequest */
        PrivateLinkResolveRequest: {
            /**
             * Private Link
             * @description Private-link value from the explicit copy field or URL fragment.
             */
            private_link?: string | null;
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
        /** RoleChangeRequest */
        RoleChangeRequest: {
            /** Reason */
            reason: string;
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "member";
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
        /** TargetPageResponse */
        TargetPageResponse: {
            /** Items */
            items: components["schemas"]["TargetResponse"][];
            /** Next Cursor */
            next_cursor?: null;
        };
        /** TargetResponse */
        TargetResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Label */
            label: string;
            /** Secondary Label */
            secondary_label: string | null;
            /** Status */
            status: string;
            /**
             * Type
             * @enum {string}
             */
            type: "user" | "club" | "event";
        };
        /** UploadGrantResponse */
        UploadGrantResponse: {
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Headers */
            headers: {
                [key: string]: string;
            };
            /**
             * Method
             * @constant
             */
            method: "PUT";
            /** Url */
            url: string;
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
    listAdminAuditEvents: {
        parameters: {
            query?: {
                action?: string | null;
                actor_user_id?: string | null;
                cursor?: string | null;
                limit?: number;
                target_id?: string | null;
                target_type?: string | null;
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
                    "application/json": components["schemas"]["AuditPageResponse"];
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
            /** @description Platform-admin access, MFA, or CSRF denied. */
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
        };
    };
    listModerationCases: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                priority?: ("standard" | "high" | "emergency") | null;
                status?: ("open" | "investigating" | "actioned" | "dismissed") | null;
                target_type?: ("user" | "club" | "event") | null;
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
                    "application/json": components["schemas"]["CasePageResponse"];
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
            /** @description Platform-admin access, MFA, or CSRF denied. */
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
        };
    };
    getModerationCase: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
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
                    "application/json": components["schemas"]["CaseDetailResponse"];
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
            /** @description Platform-admin access, MFA, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Case or target not found. */
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
    performModerationAction: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying a moderation action. */
                "Idempotency-Key": string;
            };
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActionRequest"];
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
                    "application/json": components["schemas"]["ActionResponse"];
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
            /** @description Platform-admin access, MFA, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Case or target not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Moderation transition conflicted. */
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
    searchModerationTargets: {
        parameters: {
            query: {
                limit?: number;
                query: string;
                target_type: "user" | "club" | "event";
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
                    "application/json": components["schemas"]["TargetPageResponse"];
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
            /** @description Platform-admin access, MFA, or CSRF denied. */
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
        };
    };
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
    closeClub: {
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
                "application/json": components["schemas"]["CloseClubRequest"];
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    joinClub: {
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
                "application/json": components["schemas"]["JoinClubRequest"];
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
                    "application/json": components["schemas"]["JoinClubResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    listClubJoinRequests: {
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
                    "application/json": components["schemas"]["JoinRequestPageResponse"];
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
            /** @description Resource not found. */
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
    approveClubJoinRequest: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                club_id: string;
                join_request_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionRequest"];
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    rejectClubJoinRequest: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                club_id: string;
                join_request_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionRequest"];
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    listClubMembers: {
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
                    "application/json": components["schemas"]["MemberPageResponse"];
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
            /** @description Resource not found. */
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
    changeClubMemberRole: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                club_id: string;
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RoleChangeRequest"];
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    leaveClub: {
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    transferClubOwnership: {
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
                "application/json": components["schemas"]["OwnershipTransferRequest"];
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
                    "application/json": components["schemas"]["OperationResponse"];
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
            /** @description Resource not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Membership operation conflicted with current state. */
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
    listManagedClubs: {
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
                    "application/json": components["schemas"]["ManagedClubPageResponse"];
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
    resolveEventPrivateLink: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PrivateLinkResolveRequest"] | null;
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
                    "application/json": components["schemas"]["EventAudienceResponse"];
                };
            };
            /** @description Private event access is unavailable. */
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
            /** @description Private-link resolution rate limit exceeded. */
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
    createEvent: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying event creation or duplication. */
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventCreateRequest"];
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
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Revision, lifecycle, or idempotency conflict. */
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
                    "application/json": components["schemas"]["EventAudienceResponse"];
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
    deleteDraftEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventRevisionRequest"];
            };
        };
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
            /** @description Event not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Revision, lifecycle, or idempotency conflict. */
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
    updateEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventPatchRequest"];
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
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Event not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Revision, lifecycle, or idempotency conflict. */
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
    cancelEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventRevisionRequest"];
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
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Event not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Revision, lifecycle, or idempotency conflict. */
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
    completeEvent: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EventRevisionRequest"];
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
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Event not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Revision, lifecycle, or idempotency conflict. */
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
    duplicateEvent: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying event creation or duplication. */
                "Idempotency-Key": string;
            };
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Event not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Revision, lifecycle, or idempotency conflict. */
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
    getManagedEvent: {
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
                    "application/json": components["schemas"]["ManagedEventResponse"];
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
            /** @description Event not found. */
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
    createEventPrivateLink: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PrivateLinkCreateRequest"];
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
                    "application/json": components["schemas"]["PrivateLinkIssuedResponse"];
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
            /** @description Private event access is unavailable. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Private-link state conflicts with the request. */
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
    revokeEventPrivateLink: {
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
            /** @description Private event access is unavailable. */
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
    rotateEventPrivateLink: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PrivateLinkCreateRequest"];
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
                    "application/json": components["schemas"]["PrivateLinkIssuedResponse"];
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
            /** @description Private event access is unavailable. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Private-link state conflicts with the request. */
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
    listManagedEvents: {
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
                    "application/json": components["schemas"]["ManagedEventPageResponse"];
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
    getPublicMedia: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
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
                    "application/json": unknown;
                };
            };
            /** @description Media asset not found. */
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
    createMediaUpload: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying this media mutation. */
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaUploadCreateRequest"];
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
                    "application/json": components["schemas"]["MediaUploadResponse"];
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
            /** @description Verification, capability, ownership, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Upload state or idempotency conflict. */
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
    completeMediaUpload: {
        parameters: {
            query?: never;
            header: {
                /** @description Stable key for retrying this media mutation. */
                "Idempotency-Key": string;
            };
            path: {
                asset_id: string;
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
                    "application/json": components["schemas"]["MediaAssetResponse"];
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
            /** @description Verification, capability, ownership, or CSRF denied. */
            403: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Media asset not found. */
            404: {
                headers: {
                    "X-Request-ID": components["headers"]["RequestId"];
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Upload state or idempotency conflict. */
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
            /** @description Storage temporarily unavailable. */
            503: {
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
