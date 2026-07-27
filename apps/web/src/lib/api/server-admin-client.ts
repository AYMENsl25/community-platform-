import { cookies } from "next/headers";

import { createAdminClient } from "./admin-client";

export async function createServerAdminClient() {
  const cookieStore = await cookies();
  const access = cookieStore.get("talaqi_access")?.value;
  const csrf = cookieStore.get("talaqi_csrf")?.value;
  const cookie = [
    access ? `talaqi_access=${access}` : undefined,
    csrf ? `talaqi_csrf=${csrf}` : undefined,
  ]
    .filter(Boolean)
    .join("; ");
  return createAdminClient({
    baseUrl: process.env.API_PUBLIC_URL ?? "http://localhost:8000",
    ...(cookie ? { cookie } : {}),
    ...(csrf ? { csrfToken: csrf } : {}),
  });
}
