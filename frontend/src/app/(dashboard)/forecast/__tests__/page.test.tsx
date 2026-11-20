import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForecastRunsPage from "@/app/(dashboard)/forecast/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));
const me = vi.hoisted(() => ({ role: "ppic" }));
vi.mock("@/hooks/useAuth", () => ({ useMe: () => ({ data: { role: me.role }, isPending: false }) }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ForecastRunsPage />
    </QueryClientProvider>,
  );
}

const RUN = {
  run_id: "abcdef12-0000", status: "COMPLETED", horizon: 12, horizon_unit: "months",
  created_at: "2026-11-20T08:00:00Z", created_by: "Planner A",
  n_products: 5, n_completed: 4, n_failed: 1, n_pending_selection: 2, has_planning: false,
};

describe("ForecastRunsPage (CR v3.6 §1)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    me.role = "ppic";
  });

  it("tabel run: pembuat, horizon, jumlah produk, status, pending, perencanaan, link detail", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: [RUN] } as never);
    renderPage();

    expect(await screen.findByText("Planner A")).toBeDefined();
    expect(screen.getByText("12 bulan")).toBeDefined();
    expect(screen.getByText(/4 berhasil · 1 gagal/)).toBeDefined();
    expect(screen.getByText("Selesai")).toBeDefined();
    expect(screen.getByText("2 belum dipilih")).toBeDefined();
    expect(screen.getByText("Belum")).toBeDefined();
    expect(screen.getByRole("link", { name: /buka run abcdef12/i }).getAttribute("href")).toBe("/forecast/runs/abcdef12-0000");
    expect(screen.getByRole("link", { name: /forecast baru/i }).getAttribute("href")).toBe("/forecast/new");
  });

  it("viewer tidak melihat tombol Forecast baru", async () => {
    me.role = "viewer";
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: [RUN] } as never);
    renderPage();

    await screen.findByText("Planner A");
    expect(screen.queryByRole("link", { name: /forecast baru/i })).toBeNull();
  });

  it("kosong → empty state", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: [] } as never);
    renderPage();
    expect(await screen.findByText(/belum ada forecast run/i)).toBeDefined();
  });
});
