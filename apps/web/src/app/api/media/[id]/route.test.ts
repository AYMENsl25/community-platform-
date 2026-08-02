import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const mediaId = "018f0000-0000-7000-8000-000000000299";
const context = (id: string) => ({ params: Promise.resolve({ id }) });

afterEach(() => vi.unstubAllGlobals());

describe("canonical media proxy", () => {
  it("forwards no cookies and preserves only safe image headers", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(new Uint8Array([1, 2, 3]), {
        status: 200,
        headers: {
          "Content-Type": "image/webp",
          "Cache-Control": "public, max-age=60, s-maxage=300, must-revalidate",
          "Set-Cookie": "never-forward=secret",
        },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test/";
    const response = await GET(
      new Request(`http://web.test/api/media/${mediaId}`, {
        headers: { Cookie: "private=session" },
      }),
      context(mediaId),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("image/webp");
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/media/public/${mediaId}`,
      expect.objectContaining({
        next: { revalidate: 60, tags: [`public-media:${mediaId}`] },
      }),
    );
    expect(fetcher.mock.calls[0]?.[1]).not.toHaveProperty("headers");
  });

  it("rejects malformed IDs before fetching", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    expect(
      (await GET(new Request("http://web.test"), context("bad"))).status,
    ).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
