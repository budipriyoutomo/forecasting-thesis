import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OverrideForm } from "@/components/override/OverrideForm";
import { api } from "@/lib/api";

beforeEach(() => {
  document.cookie = "fiq_token=tok; path=/";
});
afterEach(() => vi.restoreAllMocks());

function renderForm(onDone = vi.fn(), props?: Partial<ComponentProps<typeof OverrideForm>>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <OverrideForm
        targetType="reorder_recommendation"
        targetId="rec1"
        field="recommended_order_qty"
        label="Order qty baru"
        onDone={onDone}
        {...props}
      />
    </QueryClientProvider>,
  );
  return onDone;
}

describe("OverrideForm", () => {
  it("menolak submit tanpa alasan (reason wajib)", async () => {
    const spy = vi.spyOn(api.overrides, "create");
    renderForm();

    await userEvent.type(screen.getByLabelText(/order qty baru/i), "120");
    await userEvent.click(screen.getByRole("button", { name: /simpan override/i }));

    expect(await screen.findByText(/Alasan wajib diisi/i)).toBeDefined();
    expect(spy).not.toHaveBeenCalled();
  });

  it("submit dengan alasan mengirim new_value + reason", async () => {
    const spy = vi.spyOn(api.overrides, "create").mockResolvedValue({
      success: true,
      data: {
        id: "o1",
        target_type: "reorder_recommendation",
        target_id: "rec1",
        user_id: "u1",
        previous_value: { recommended_order_qty: "87" },
        new_value: { recommended_order_qty: 120 },
        reason: "produksi tambahan",
        created_at: null,
      },
    });
    const onDone = renderForm();

    await userEvent.type(screen.getByLabelText(/order qty baru/i), "120");
    await userEvent.type(screen.getByLabelText(/alasan override/i), "produksi tambahan");
    await userEvent.click(screen.getByRole("button", { name: /simpan override/i }));

    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(
      {
        target_type: "reorder_recommendation",
        target_id: "rec1",
        new_value: { recommended_order_qty: 120 },
        reason: "produksi tambahan",
      },
      "tok",
    );
  });
});
