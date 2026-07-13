import createClient from "openapi-fetch";
import type { Client } from "openapi-fetch";

import type { paths } from "./schema.generated";

export type TalaqiClient = Client<paths>;

export interface TalaqiClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
}

export function createTalaqiClient(options: TalaqiClientOptions): TalaqiClient {
  if (options.baseUrl.length === 0) {
    throw new TypeError("baseUrl is required");
  }
  return createClient<paths>({
    baseUrl: options.baseUrl,
    ...(options.fetch === undefined ? {} : { fetch: options.fetch }),
  });
}

export type { components, operations, paths } from "./schema.generated";
