import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "./login-form";

afterEach(() => vi.unstubAllGlobals());

describe("LoginForm", () => {
  it("submits credentials through the same-origin proxy", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(Response.json({ authenticated: true }));
    vi.stubGlobal("fetch", fetcher);
    render(<LoginForm locale="en" returnTo="/events/event-id" />);

    fireEvent.change(screen.getByLabelText("Email or username"), {
      target: { value: "member@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "example-password" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in securely" }));

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    expect(fetcher).toHaveBeenCalledWith(
      "/api/public/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("shows a non-enumerating localized error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(Response.json({}, { status: 401 })),
    );
    render(<LoginForm locale="en" returnTo="/" />);

    fireEvent.change(screen.getByLabelText("Email or username"), {
      target: { value: "missing@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-password" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in securely" }));

    expect(
      await screen.findByText("Check your sign-in information and try again."),
    ).toBeInTheDocument();
  });
});
