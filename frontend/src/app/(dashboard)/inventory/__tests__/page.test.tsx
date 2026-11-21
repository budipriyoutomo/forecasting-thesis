import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InventoryPage from "@/app/(dashboard)/inventory/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok", clearToken: () => {} }));

const MATERIALS = [{ id: "m1", code: "BTL", name: "Botol", unit: "PCS", lead_time_days: 7 }];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <InventoryPage />
    </QueryClientProvider>,
  );
}

// CR v3.5 §5.2 — riwayat snapshot & pemakaian per material, terbuka untuk semua role.
describe("InventoryPage — riwayat per material", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.materials, "list").mockResolvedValue({ success: true, data: MATERIALS } as never);
    vi.spyOn(api.products, "list").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.inventory, "latest").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.inventory, "wasteFactors").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { role: "viewer" } } as never);
  });

  it("riwayat stok baru dimuat setelah material dipilih", async () => {
    const snapshots = vi.spyOn(api.inventory, "snapshots").mockResolvedValue({
      success: true, data: [{ material_id: "m1", snapshot_date: "2026-10-01", qty: 1200, uom: "PCS" }],
    } as never);
    renderPage();

    const section = await screen.findByRole("region", { name: /riwayat stok erp/i });
    expect(snapshots).not.toHaveBeenCalled();
    await within(section).findByRole("option", { name: /BTL — Botol/ });
    await userEvent.selectOptions(within(section).getByLabelText(/material/i), "m1");

    expect(await within(section).findByText("1.200")).toBeDefined();
    expect(snapshots).toHaveBeenCalledWith("m1", "tok");
  });
});

// Setiap tombol import punya template unduhan + catatan pengisian (hanya untuk role yang boleh import).
describe("InventoryPage — template import", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.materials, "list").mockResolvedValue({ success: true, data: MATERIALS } as never);
    vi.spyOn(api.products, "list").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.inventory, "latest").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.inventory, "wasteFactors").mockResolvedValue({ success: true, data: [] } as never);
  });

  it("tab stok & pemakaian masing-masing punya tombol unduh template untuk admin", async () => {
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { role: "admin" } } as never);
    renderPage();

    expect(await screen.findByRole("button", { name: /unduh template stok/i })).toBeDefined();
    await userEvent.click(screen.getByRole("tab", { name: /pemakaian aktual/i }));
    expect(await screen.findByRole("button", { name: /unduh template pemakaian/i })).toBeDefined();
  });

  it("viewer tidak melihat template (tidak bisa import)", async () => {
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { role: "viewer" } } as never);
    renderPage();

    await screen.findByRole("region", { name: /riwayat stok erp/i });
    expect(screen.queryByRole("button", { name: /unduh template/i })).toBeNull();
  });
});
