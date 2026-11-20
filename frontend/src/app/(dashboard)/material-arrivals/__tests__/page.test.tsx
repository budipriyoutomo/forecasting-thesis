import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MaterialArrivalsPage from "@/app/(dashboard)/material-arrivals/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));

const RUNS = [
  { run_id: "r2", status: "COMPLETED", horizon: 12, horizon_unit: "days", created_at: "2026-11-20T08:00:00+00:00" },
  { run_id: "r1", status: "COMPLETED", horizon: 12, horizon_unit: "days", created_at: "2026-11-01T08:00:00+00:00" },
];
const ROW = {
  material_id: "m1", scenario: "proposed", period: "2026-11-01", opening_qty: 100, receipt_qty: null,
  usage_qty: 80, order_qty: 500, ending_qty: 520, shortage_qty: 0, capacity_qty: null,
  utilization_opening_pct: null, utilization_ending_pct: null, is_within_capacity: null,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MaterialArrivalsPage />
    </QueryClientProvider>,
  );
}

describe("MaterialArrivalsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.materials, "list").mockResolvedValue({
      success: true, data: [{ id: "m1", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" }],
    } as never);
    vi.spyOn(api.reorder, "list").mockResolvedValue({
      success: true, data: [{ material_id: "m1", reorder_point: "150", order_qty_policy_used: "eoq" }],
    } as never);
  });

  it("memakai run terbaru secara default dan menampilkan kedatangan hasil ROP", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: RUNS } as never);
    const projection = vi.spyOn(api.planning, "projection").mockResolvedValue({ success: true, data: [ROW] } as never);
    renderPage();

    expect(await screen.findByText("BTL-WHITE — Bottle White")).toBeDefined();
    expect(projection).toHaveBeenCalledWith("r2", "tok");
    expect(screen.queryByRole("button", { name: /import/i })).toBeNull(); // read-only
    // CR v3.6 §1 — tautan ke detail run
    expect(screen.getByRole("link", { name: /lihat detail run/i }).getAttribute("href")).toBe("/forecast/runs/r2");
  });

  it("ganti run memuat proyeksi run itu", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: RUNS } as never);
    const projection = vi.spyOn(api.planning, "projection").mockResolvedValue({ success: true, data: [] } as never);
    renderPage();

    // CR v3.6 §8.3 — RunPicker memakai ui/select (Radix): buka dulu, lalu pilih opsi
    await userEvent.click(await screen.findByRole("combobox", { name: /forecast run/i }));
    await userEvent.click((await screen.findAllByRole("option"))[1]);
    await waitFor(() => expect(projection).toHaveBeenCalledWith("r1", "tok"));
  });

  it("pemilih run menampilkan pembuat run (semua run terlihat, CR v3.5 §3.4)", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({
      success: true, data: [{ ...RUNS[0], created_by: "Planner PPIC" }, RUNS[1]],
    } as never);
    vi.spyOn(api.planning, "projection").mockResolvedValue({ success: true, data: [] } as never);
    renderPage();

    await userEvent.click(await screen.findByRole("combobox", { name: /forecast run/i }));
    const options = (await screen.findAllByRole("option")).map((o) => o.textContent);
    expect(options[0]).toMatch(/oleh Planner PPIC/);
    expect(options[1]).not.toMatch(/oleh/);
  });

  it("belum ada run → arahkan ke halaman forecast", async () => {
    vi.spyOn(api.forecast, "listRuns").mockResolvedValue({ success: true, data: [] } as never);
    renderPage();
    expect(await screen.findByText(/belum ada forecast run/i)).toBeDefined();
  });
});
