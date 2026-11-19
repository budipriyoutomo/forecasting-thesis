import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CapacityAdjustmentPanel } from "@/components/planning/CapacityAdjustmentPanel";
import { api } from "@/lib/api";
import type { CapacitySuggestion } from "@/types/planning";

beforeEach(() => {
  document.cookie = "fiq_token=tok; path=/";
});
afterEach(() => vi.restoreAllMocks());

const materials = [
  { id: "m1", code: "CAP-RED", name: "Cap Red", category: "Cap", unit: "PCS" },
] as never[];

const suggestion: CapacitySuggestion = {
  status: "adjusted",
  target_service_level_pct: 99,
  iterations: 2,
  groups: [
    { group: "cap", capacity_qty: 2450, excess_before: 66, excess_after: 0, service_level_pct: 97,
      status: "adjusted", cause: null },
  ],
  items: [
    { material_id: "m1", group: "cap", safety_stock_before: 465.27, safety_stock_after: 376.16,
      buffer_stock_before: 50, buffer_stock_after: 50, reorder_point_before: 1515.27, reorder_point_after: 1426.16,
      service_level_before: 99, service_level_after: 97, service_level_pct: 97 },
  ],
};

function renderPanel(props: Partial<Parameters<typeof CapacityAdjustmentPanel>[0]> = {}) {
  const onReplan = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <CapacityAdjustmentPanel
        runId="r1"
        suggestion={suggestion}
        adjustedCount={0}
        materials={materials}
        onReplan={onReplan}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { onReplan, ...view };
}

const okSave = () =>
  vi.spyOn(api.capacityAdjustments, "save").mockResolvedValue({ success: true, data: [] });

describe("CapacityAdjustmentPanel", () => {
  it("menampilkan usulan per grup & material", () => {
    renderPanel();
    expect(screen.getByText(/melebihi kapasitas gudang/i)).toBeDefined();
    expect(screen.getByText("CAP-RED — Cap Red")).toBeDefined();
    // service level grup (target → anak tangga) & α efektif material
    expect(screen.getAllByText("99% → 97%")).toHaveLength(2);
    expect(screen.getByText(/465,27 → 376,16/)).toBeDefined(); // SS sistem → usulan
  });

  it("terima usulan menyimpan source suggested lalu menjalankan ulang perencanaan", async () => {
    const spy = okSave();
    const { onReplan } = renderPanel();
    await userEvent.click(screen.getByRole("button", { name: /terima usulan/i }));
    await waitFor(() => expect(onReplan).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(
      "r1",
      {
        source: "suggested",
        items: [{ material_id: "m1", safety_stock: 376.16, buffer_stock: 50, service_level_pct: 97 }],
        reason: null,
      },
      "tok",
    );
  });

  it("custom wajib alasan", async () => {
    const spy = okSave();
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: /simpan custom/i }));
    expect(await screen.findByText(/alasan wajib diisi/i)).toBeDefined();
    expect(spy).not.toHaveBeenCalled();
  });

  it("custom mengirim angka isian planner", async () => {
    const spy = okSave();
    const { onReplan } = renderPanel();
    const ss = screen.getByLabelText(/SS custom CAP-RED/i);
    await userEvent.clear(ss);
    await userEvent.type(ss, "300");
    const buffer = screen.getByLabelText(/Buffer custom CAP-RED/i);
    await userEvent.clear(buffer);
    await userEvent.type(buffer, "10");
    await userEvent.type(screen.getByLabelText(/alasan adjust custom/i), "Gudang disewa sebagian");
    await userEvent.click(screen.getByRole("button", { name: /simpan custom/i }));
    await waitFor(() => expect(onReplan).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(
      "r1",
      { source: "custom", items: [{ material_id: "m1", safety_stock: 300, buffer_stock: 10 }],
        reason: "Gudang disewa sebagian" },
      "tok",
    );
  }, 30000);

  it("infeasible menampilkan penyebab", () => {
    renderPanel({
      suggestion: {
        ...suggestion,
        status: "infeasible",
        groups: [{ ...suggestion.groups[0], status: "infeasible", excess_after: 157, cause: "opening_stock" }],
      },
    });
    expect(screen.getByText(/tidak cukup/i)).toBeDefined();
    expect(screen.getByText(/stok awal/i)).toBeDefined();
  });

  it("sudah di-adjust & muat: tampilkan info dan tombol kembali ke nilai sistem", async () => {
    const spy = vi.spyOn(api.capacityAdjustments, "reset").mockResolvedValue({ success: true, data: { n_reset: 1 } });
    const { onReplan } = renderPanel({ suggestion: null, adjustedCount: 1 });
    expect(screen.getByText(/1 material memakai adjust/i)).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: /kembali ke nilai sistem/i }));
    await waitFor(() => expect(onReplan).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith("r1", null, "tok");
  });

  it("tanpa usulan & tanpa adjust tidak merender apa pun", () => {
    const { container } = renderPanel({ suggestion: null, adjustedCount: 0 });
    expect(container.textContent).toBe("");
  });
});
