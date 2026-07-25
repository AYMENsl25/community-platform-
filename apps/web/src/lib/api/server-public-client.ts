import { cookies } from "next/headers";

import { createPublicClient } from "./public-client";

export async function createServerPublicClient() {
  const cookieStore = await cookies();
  const access = cookieStore.get("talaqi_access")?.value;
  return createPublicClient({
    baseUrl: process.env.API_PUBLIC_URL ?? "http://localhost:8000",
    ...(access ? { cookie: `talaqi_access=${access}` } : {}),
  });
}
