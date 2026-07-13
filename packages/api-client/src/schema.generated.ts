export interface paths {
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
