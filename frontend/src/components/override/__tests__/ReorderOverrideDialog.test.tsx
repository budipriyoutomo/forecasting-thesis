import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReorderOverrideDialog } from "@/components/override/ReorderOverrideDialog";
import { api } from "@/lib/api";
import type { ReorderRecommendation } from "@/types/reorder";

const REC: ReorderRecommendation = {
  id: "rec-1", material_id: "m1", safety_stock: "6.6", reorder_point: "46.6",
  recommended_order_qty: "87", status: "urgent", order_qty_policy_used: "eoq",
};

beforeEach(() => {
  document.cookie = "fiq_token=tok; path=/";
});
afterEach(() => vi.restoreAllMocks());

function renderDialog(rec: ReorderRecommendation | null, onClose = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ReorderOverrideDialog runId="r1" recommendation={rec} materialLabel="CAP-BLUE — Cap Blue" onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

describe("ReorderOverrideDialog", () => {
  it("tertutup bila tidak ada rekomendasi", () => {
    renderDialog(null);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("menampilkan material, qty sistem, form & riwayat override", async () => {
    vi.spyOn(api.overrides, "listReorder").mockResolvedValue({
      success: true,
      data: [{
        id: "ov1", target_type: "reorder_recommendation", target_id: "rec-1", user_id: "u1",
        previous_value: { recommended_order_qty: "80" }, new_value: { recommended_order_qty: 100 },
        reason: "Promo Lebaran", created_at: "2026-11-01T00:00:00Z",
      }],
    });
    renderDialog(REC);

    const dialog = screen.getByRole("dialog");
    expect(dialog.textContent).toMatch(/CAP-BLUE/);
    expect(dialog.textContent).toMatch(/87/);
    expect(dialog.textContent).toMatch(/kelipatan eoq/i);
    expect(screen.getByLabelText(/qty pesan baru/i)).toBeDefined();
    expect(await screen.findByText(/promo lebaran/i)).toBeDefined();
  });

  it("simpan override → POST target reorder_recommendation lalu tutup", async () => {
    vi.spyOn(api.overrides, "listReorder").mockResolvedValue({ success: true, data: [] });
    const create = vi.spyOn(api.overrides, "create").mockResolvedValue({
      success: true,
      data: {
        id: "ov2", target_type: "reorder_recommendation", target_id: "rec-1", user_id: "u1",
        previous_value: null, new_value: { recommended_order_qty: 120 }, reason: "x", created_at: null,
      },
    });
    const onClose = renderDialog(REC);

    await userEvent.type(screen.getByLabelText(/qty pesan baru/i), "120");
    await userEvent.type(screen.getByLabelText(/alasan/i), "Kontrak supplier");
    await userEvent.click(screen.getByRole("button", { name: /simpan override/i }));

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        { target_type: "reorder_recommendation", target_id: "rec-1",
          new_value: { recommended_order_qty: 120 }, reason: "Kontrak supplier" },
        "tok",
      ),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("riwayat diambil per run + material, ada petunjuk jalankan ulang perencanaan", async () => {
    const list = vi.spyOn(api.overrides, "listReorder").mockResolvedValue({ success: true, data: [] });
    renderDialog({ ...REC, override_qty: "150", override_reason: "Kontrak" });
    await waitFor(() => expect(list).toHaveBeenCalledWith("r1", "m1", "tok"));
    const dialog = screen.getByRole("dialog");
    expect(dialog.textContent).toMatch(/override berlaku 150/i);
    expect(dialog.textContent).toMatch(/jalankan perencanaan/i);
  });
});
