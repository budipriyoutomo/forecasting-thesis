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
});
