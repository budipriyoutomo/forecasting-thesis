import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExternalVariablesTable } from "@/components/external-variables/ExternalVariablesTable";
import type { ExternalVariable } from "@/types/externalVariable";

const VARS: ExternalVariable[] = [
  { id: "v1", code: "suhu", name: "Suhu", value_type: "numeric", scope: "global", unit: "°C",
    description: null, is_active: true, n_values: 24 },
  { id: "v2", code: "promo", name: "Promosi", value_type: "flag", scope: "product", unit: null,
    description: null, is_active: false, n_values: 0 },
];

describe("ExternalVariablesTable", () => {
  it("menampilkan tipe, cakupan, jumlah nilai", () => {
    render(<ExternalVariablesTable variables={VARS} onToggle={vi.fn()} />);
    expect(screen.getByText("suhu")).toBeDefined();
    expect(screen.getByText("24")).toBeDefined();
    expect(screen.getByText(/per produk/i)).toBeDefined();
  });

  it("toggle aktif memanggil onToggle dengan nilai baru", async () => {
    const onToggle = vi.fn();
    render(<ExternalVariablesTable variables={VARS} onToggle={onToggle} />);

    await userEvent.click(screen.getByRole("switch", { name: /aktifkan promo/i }));
    expect(onToggle).toHaveBeenCalledWith(VARS[1], true);
    expect(screen.getByRole("switch", { name: /aktifkan suhu/i }).getAttribute("aria-checked")).toBe("true");
  });

  it("kolom kelengkapan: merah bila < 100%", () => {
    render(
      <ExternalVariablesTable
        variables={VARS}
        onToggle={vi.fn()}
        coverage={{
          v1: { variable_id: "v1", code: "suhu", first_period: "2024-01-01", last_period: "2025-12-01",
            n_expected: 36, n_filled: 24, missing_periods: ["2026-01-01", "2026-02-01"] },
          v2: { variable_id: "v2", code: "promo", first_period: "2024-01-01", last_period: "2026-12-01",
            n_expected: 36, n_filled: 36, missing_periods: [] },
        }}
      />,
    );
    const partial = screen.getByText("24/36 (67%)");
    expect(partial.className).toContain("text-destructive");
    expect(partial.className).toContain("whitespace-nowrap"); // "24/36 (67%)" tidak terpotong 2 baris
    expect(partial.getAttribute("title")).toContain("2026-01-01");
    expect(screen.getByText("36/36 (100%)").className).not.toContain("text-destructive");
  });
});
