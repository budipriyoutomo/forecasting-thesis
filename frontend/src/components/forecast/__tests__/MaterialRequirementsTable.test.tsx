import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MaterialRequirementsTable } from "@/components/forecast/MaterialRequirementsTable";
import { api } from "@/lib/api";
import type { MaterialRequirement } from "@/types/forecast";

beforeEach(() => {
  document.cookie = "fiq_token=tok; path=/";
});
afterEach(() => vi.restoreAllMocks());

const rows: MaterialRequirement[] = [
  {
    id: "req1",
    run_id: "run1",
    material_id: "M1",
    forecast_qty: "1200.5",
    standard_usage_qty: "1300",
    actual_usage_qty: "1250",
    buffer_stock_pct: "3.85",
  },
  {
    id: "req2",
    run_id: "run1",
    material_id: "M2",
    forecast_qty: "600",
    standard_usage_qty: null,
    actual_usage_qty: null,
    buffer_stock_pct: null,
  },
];

function renderTable(requirements = rows) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MaterialRequirementsTable requirements={requirements} />
    </QueryClientProvider>,
  );
}

describe("MaterialRequirementsTable", () => {
  it("menampilkan kebutuhan tiap material hasil breakdown BOM", () => {
    renderTable();
    expect(screen.getByText("M1")).toBeDefined();
    expect(screen.getByText("M2")).toBeDefined();
    expect(screen.getByText("1.200,5")).toBeDefined();
  });

  it("menampilkan tanda strip untuk kolom yang belum terisi", () => {
    renderTable([rows[1]]);
    // standard/actual/buffer null → jangan render "null" atau "NaN"
    expect(screen.queryByText(/null|NaN/)).toBeNull();
  });

  it("menampilkan pesan kosong bila run belum punya kebutuhan material", () => {
    renderTable([]);
    expect(screen.getByText(/belum ada kebutuhan material/i)).toBeDefined();
  });

  it("override baris mengirim target_type material_requirement + id baris", async () => {
    const spy = vi.spyOn(api.overrides, "create").mockResolvedValue({
      success: true,
      data: {
        id: "o1",
        target_type: "material_requirement",
        target_id: "req1",
        user_id: "u1",
        previous_value: { forecast_qty: "1200.5" },
        new_value: { forecast_qty: 1400 },
        reason: "rework batch sebelumnya",
        created_at: null,
      },
    });
    renderTable();

    await userEvent.click(screen.getAllByRole("button", { name: /override/i })[0]);
    await userEvent.type(screen.getByLabelText(/kebutuhan material/i), "1400");
    await userEvent.type(screen.getByLabelText(/alasan override/i), "rework batch sebelumnya");
    await userEvent.click(screen.getByRole("button", { name: /simpan override/i }));

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        {
          target_type: "material_requirement",
          target_id: "req1",
          new_value: { forecast_qty: 1400 },
          reason: "rework batch sebelumnya",
        },
        "tok",
      ),
    );
  });
});
