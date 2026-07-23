import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BackendStatus } from "@/components/dashboard/BackendStatus";
import { api } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("BackendStatus", () => {
  it("menampilkan status terhubung saat backend membalas success", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ success: true, data: { status: "ok" } });

    renderWithQuery(<BackendStatus />);

    expect(await screen.findByText(/Backend terhubung/i)).toBeDefined();
  });

  it("menampilkan status gagal saat backend tidak bisa dihubungi", async () => {
    vi.spyOn(api, "health").mockRejectedValue(new Error("network error"));

    renderWithQuery(<BackendStatus />);

    expect(await screen.findByText(/Backend tidak terhubung/i)).toBeDefined();
  });

  it("menampilkan status gagal saat backend membalas envelope error", async () => {
    vi.spyOn(api, "health").mockResolvedValue({
      success: false,
      error: { code: "RATE_LIMIT_EXCEEDED", message: "terlalu banyak request" },
    });

    renderWithQuery(<BackendStatus />);

    expect(await screen.findByText(/Backend tidak terhubung/i)).toBeDefined();
  });
});
