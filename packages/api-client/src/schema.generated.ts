export interface paths {
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
